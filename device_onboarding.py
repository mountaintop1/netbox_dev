from extras.scripts import *
from django.utils.text import slugify
from django.contrib.contenttypes.models import ContentType
from typing import Tuple

from dcim.choices import DeviceStatusChoices
from dcim.models import Device, DeviceRole, DeviceType, Site, Platform, Interface, Manufacturer, VirtualChassis
from ipam.models import IPAddress, VLAN, VLANGroup 
from extras.models import ConfigTemplate

def to_one_ended(new_int: str) -> str:
    return new_int[:-1] + "1"


def replace_slot(interface: str, new_slot: int) -> str:
    """
    Replace the first number after the interface type with the given integer.
    Example: "GigabitEthernet1/0/1", 2 -> "GigabitEthernet2/0/1"
    """
    # Find where the digits start
    i = 0
    while i < len(interface) and not interface[i].isdigit():
        i += 1
    if i == len(interface):
        raise ValueError("No numeric part found in the interface string.")

    # Find the end of the first numeric segment
    j = i
    while j < len(interface) and interface[j].isdigit():
        j += 1

    return interface[:i] + str(new_slot) + interface[j:]

def per_switch_with_adding(ap_count: int, num_switches: int) -> Tuple[int,int,int]:
    if num_switches < 1:
        raise ValueError("num_switches must be >= 1")
    # minimal total that is a multiple of num_switches and >= ap_count
    remainder = ap_count % num_switches
    added = 0 if remainder == 0 else (num_switches - remainder)
    total = ap_count + added
    per_switch = total // num_switches
    return per_switch, total, added

def add_member_to_vc(device: Device, vc: VirtualChassis, position: int, priority: int):
    device.virtual_chassis = vc
    device.vc_priority = priority
    device.vc_position = position
    device.save()

def distribute_items(main_list, ap_count=None, guest_count=None):
    """
    Distribute up to ap_count items to ap_list and up to guest_count items to guest_list.
    Removes assigned items from main_list (returned as a new list).
    Returns (ap_list, guest_list, main_list).
    """
    ap_list = []
    guest_list = []

    # Assign to ap_list
    if isinstance(ap_count, int) and ap_count > 0:
        take_ap = min(ap_count, len(main_list))
        ap_list = main_list[:take_ap]
        main_list = main_list[take_ap:]

    # Assign to guest_list (after ap_list has taken its share)
    if isinstance(guest_count, int) and guest_count > 0:
        take_guest = min(guest_count, len(main_list))
        guest_list = main_list[:take_guest]
        main_list = main_list[take_guest:]

    return main_list, ap_list, guest_list

CHOICES = (
    ('TenGigabitEthernet1/1/1', 'Te1/1/1'),
    ('TenGigabitEthernet1/1/2', 'Te1/1/2'),
    ('TenGigabitEthernet1/1/3', 'Te1/1/3'),
    ('TenGigabitEthernet1/1/4', 'Te1/1/4'),
    ('TwentyFiveGigabitEthernet1/1/1', 'Twe1/1/1'),
    ('TwentyFiveGigabitEthernet1/1/2', 'Twe1/1/2'),
    ('GigabitEthernet1/1', 'Gi1/1'),
    ('GigabitEthernet1/2', 'Gi1/2'),
)

LAG_CHOICES = (
    ('Po1', 'Po1'),
    ('Po2', 'Po2'),
    ('Po3', 'Po3'),
)

choices1 = (
    ('TenGigabitEthernet1/1/1', 'Te1/1/1'),
    ('TenGigabitEthernet1/1/2', 'Te1/1/2'),
    ('TenGigabitEthernet1/1/3', 'Te1/1/3'),
    ('TenGigabitEthernet1/1/4', 'Te1/1/4'),
)

choices2 = (
    ('GigabitEthernet1/1/1', 'Gi1/1/1'),
    ('GigabitEthernet1/1/2', 'Gi1/1/2'),
    ('TenGigabitEthernet1/1/3', 'Te1/1/3'),
    ('TenGigabitEthernet1/1/4', 'Te1/1/4'),
)

choices3 = (
    ('TwentyFiveGigabitEthernet1/1/1', 'Twe1/1/1'),
    ('TwentyFiveGigabitEthernet1/1/2', 'Twe1/1/2'),
    ('TwentyFiveGigabitEthernet1/1/3', 'Twe1/1/3'),
    ('TwentyFiveGigabitEthernet1/1/4', 'Twe1/1/4'),
)

choices4 = (
    ('GigabitEthernet1/1', 'Gi1/1'),
    ('GigabitEthernet1/2', 'Gi1/2'),
    ('GigabitEthernet1/3', 'Gi1/3'),
    ('GigabitEthernet1/4', 'Gi1/4'),
)

CHOICES_BY_MODEL = {
    "cisco-c9300l-24p-4x": choices1,
    "cisco-c9300l-48uxg-4x": choices1,
    "cisco-c9300lm-24u-4y": choices3,
    "cisco-c9200cx-12p-2x2g": choices2,
    "cisco-ie-4000-8gt8gp4g-e": choices4,
}
    
def uplink_choices(data=None):
    # NetBox may call with no args or with a dict of current form values
    if not isinstance(data, dict):
        return ()
    dt = data.get("switch_model")  # DeviceType instance or None
    if not dt:
        return ()
    slug = dt.slug  # ensure a string key
    return CHOICES_BY_MODEL.get(slug, ())

class DeviceOnboarding(Script):

    class Meta:
        name = "Device Onboarding"
        description = "Provision a New switch to Site"
        commit_default = False
        fieldsets = (
            ('Device Object', ('device_name', 'switch_model', 'mgmt_address', 'gateway_address', 'is_stack_switch')),
            ('Site Object', ('site', 'mgmt_vlan', 'blan_vlan', 'guest_vlan')),
            ('Connected Access Point', ('ap_count',)),
            ('Wired Guest', ('guest_count',)),
            ('Uplink Port 1', ('uplink_1', 'uplink_desc_a',)),
            ('Uplink Port 2', ('uplink_2', 'uplink_desc_b',)),
            ('Lag Interface', ('lag_name', 'lag_desc')),
        )
    
    device_name = StringVar(
        description="Device hostname",
        label='Device Name'
    )
    switch_model = ObjectVar(
        description="Access switch model",
        model=DeviceType,
        label='Device Model'
    )
    site = ObjectVar(
        description="Choose Site name from drop-down",
        model=Site,
        label='Site Name'
    )
    mgmt_address = IPAddressWithMaskVar(
        description="Device Mgmt IP example: 192.168.20.10/23",
        label='Mgmt IP Address'
    )
    gateway_address = StringVar(
        description="Default Gateway. example: 10.10.10.1",
        label='Default Gateway',
    )
    is_stack_switch = BooleanVar(
        description="Is this a stack switch",
        default=False,
        label='is_stack',
    )
    mgmt_vlan = IntegerVar(
        description="Mgmt VLAN ID example: 60",
        label='Mgmt VLAN ID',
        default=60,
        min_value=2,
        max_value=4096,
    )
    blan_vlan = IntegerVar(
        description="Business LAN VLAN ID example: 1101",
        label='BLAN VLAN ID',
        min_value=2,
        max_value=4096,
    )
    guest_vlan = IntegerVar(
        description="Guest VLAN ID example: 3101",
        label='Guest VLAN ID',
        min_value=2,
        max_value=4096,
    )
    ap_count = IntegerVar(
        description="Number of access point to be install on the switch",
        label='AP Count',
        required=False,
        min_value=1,
        max_value=10,
    )
    guest_count = IntegerVar(
        description="Number of wired guest users that need access on the switch",
        label='Guest Count',
        required=False,
        min_value=1,
        max_value=10,
    )
    uplink_1 = ChoiceVar(
        choices=CHOICES,
        description="Uplink Interface drop-down",
        label='Uplink Interface',
    )
    uplink_desc_a = StringVar(
        description="Uplink Port 1 Interface Description",
        label='Uplink Interface Description',
        default='remotehost=os-z07-41ra0043-01-sw-lef-a; port=xe-0/0/18',
    )
    uplink_2 = ChoiceVar(
        choices=CHOICES,
        description="Uplink Interface drop-down",
        label='Uplink Interface',
    )
    uplink_desc_b = StringVar(
        description="Uplink Port 2 Interface Description",
        label='Uplink Interface Description',
        default='remotehost=os-z07-41ra0043-01-sw-lef-b; port=xe-0/0/18'
    )
    lag_name  = ChoiceVar(
        choices=LAG_CHOICES,
        description="Uplink Port 1/2 Lag Interface drop-down. example: Po1/ae1",
        label='Lag Interface Name',
        default='Po1',
    )
    lag_desc = StringVar(
        description="Uplink Port 1/2 Lag Interface description",
        label='Lag Interface Description',
        default='remotehost=os-z07-41ra0043-01-sw-lef-a/b; port=ae18'
    )
    def run(self, data, commit):

        # Create access switches
        switch_role = DeviceRole.objects.get(name='Access Switch')
        platform = Platform.objects.get(slug='ios')
        mfr = Manufacturer.objects.get(slug="cisco")
        switch = Device.objects.create(
            device_type=data['switch_model'],
            name=data['device_name'],
            site=data['site'],
            status=DeviceStatusChoices.STATUS_ACTIVE,
            role=switch_role,
            platform=platform,
            config_template=ConfigTemplate.objects.get(name='master_temp_acc_v1'),
        )
        switch.custom_field_data["gateway"] = data["gateway_address"]
        switch.full_clean()
        switch.save()
        switch.refresh_from_db()
        self.log_success(f"Created new switch: {switch} with {switch.interfaces.all().count()} interfaces")
        vlan_group = VLANGroup.objects.create(
                        name=data["device_name"],
                        slug=slugify(data["device_name"]),
                        scope_type=ContentType.objects.get_for_model(Site),
                        scope_id=data['site'].id,
                        description="vlan_grp",
                    )
        self.log_success(f"Created new vlan group: {vlan_group}")
        blan = VLAN.objects.create(
                        group=vlan_group,
                        vid=data["blan_vlan"],
                        name="blan",
                        status="active",
                        site=data['site'],
                        description="Business LAN",
                    )
        mgmt = VLAN.objects.create(
                group=vlan_group,
                vid=data["mgmt_vlan"],
                name="mgmt",
                status="active",
                site=data['site'],
                description="Mgmt Vlan",
            )
        guest = VLAN.objects.create(
                group=vlan_group,
                vid=data["guest_vlan"],
                name="guest",
                status="active",
                site=data['site'],
                description="Guest Vlan",
            )
        self.log_success(f"Created new vlans and added to group: VLANGroup: {vlan_group}, VLANs: {blan}:{mgmt}:{guest}")
        interface_portc = Interface.objects.create(
            device=switch, 
            name=data["lag_name"], 
            type="lag", 
            description=data["lag_desc"],
            mode='tagged'
        )
        interface_mgmt = Interface.objects.create(
            device=switch, 
            name=f'vlan{str(data["mgmt_vlan"])}', 
            type="virtual", 
            description="mgmt",
            mode='tagged'
        )
        self.log_success(f"Created new Po1 and mgmt int vlan: {interface_mgmt}, Portchannel:{interface_portc}")

        mgmt_ip = IPAddress.objects.create(
            address=data['mgmt_address'],
            status="active",
            description=data["device_name"],
        )
        self.log_success(f"Created IP Address: Mgmt IP: {mgmt_ip}")
        
        mgmt_ip.assigned_object = interface_mgmt
        mgmt_ip.save()
        
        switch.primary_ip4 = mgmt_ip
        switch.save()
        self.log_success(f"IP Address assigned as primary IPv4 address: {switch.primary_ip4.address}")

        usable_int = switch.interfaces.filter(name__contains='/0/').reverse()
        blan_list, ap_list, guest_list = distribute_items(usable_int, data["ap_count"], data["guest_count"])
        
        self.log_success(f"List of access port generated: {len(blan_list)}, {len(ap_list)}, {len(guest_list)}")

        for idx, ap_int in enumerate(ap_list, start=1):
            ap_int.mode = "tagged"
            ap_int.description = f"<<remotehost={data['device_name']}-wif-0{idx}>>"
            ap_int.untagged_vlan = blan
            ap_int.full_clean()
            ap_int.save()
            ap_int.tagged_vlans.add(blan,)
            
        for b_int in blan_list:
            b_int.mode = "access"
            b_int.description = "<<remotehost=User>>"
            b_int.untagged_vlan = blan
            b_int.full_clean()
            b_int.save()
    
        for g_int in guest_list:
            g_int.mode = "access"
            g_int.description = "<<remotehost=User>>"
            g_int.untagged_vlan = guest
            g_int.full_clean()
            g_int.save()
            
        self.log_success("Updated all interfaces....................................")

        lag_int = switch.interfaces.get(name=data["lag_name"])
        lag_int.tagged_vlans.add(blan, mgmt, guest)
        lag_int.full_clean()
        lag_int.save()
        self.log_success(f"Update interface Lag: {lag_int}")

        uplink1_int = switch.interfaces.get(name=data["uplink_1"])
        uplink1_int.mode = "tagged"
        uplink1_int.description = f"<<{data['uplink_desc_a']}>>"
        uplink1_int.lag = switch.interfaces.get(name=data["lag_name"])
        
        uplink1_int.full_clean()
        uplink1_int.save()
        
        uplink1_int.tagged_vlans.set([blan, mgmt, guest])
        uplink1_int.save()
        uplink1_int.refresh_from_db()
        self.log_success(f"Update uplink 1: {uplink1_int} tagged={list(uplink1_int.tagged_vlans.values_list('vid', flat=True))}")
        
        uplink2_int = switch.interfaces.get(name=data["uplink_2"])
        uplink2_int.mode = "tagged"
        uplink2_int.description = f"<<{data['uplink_desc_b']}>>"
        uplink2_int.lag = switch.interfaces.get(name=data["lag_name"])
        
        uplink2_int.full_clean()
        uplink2_int.save()
        
        uplink2_int.tagged_vlans.set([blan, mgmt, guest])
        uplink2_int.save()
        uplink2_int.refresh_from_db()
        self.log_success(f"Update uplink 2: {uplink2_int} tagged={list(uplink2_int.tagged_vlans.values_list('vid', flat=True))}")


class DeviceOnboardingVersioning(Script):
    class Meta:
        name = "Device Onboarding Autopilot"
        description = "Automatically selects the optimal uplink for each device model, with full support for stacked switches"
        commit_default = False
        fieldsets = (
            ('Device Object', ('device_name', 'switch_model', 'mgmt_address', 'gateway_address', 'is_stack_switch', 'stack_member_count')),
            ('Site Object', ('site', 'mgmt_vlan', 'blan_vlan', 'guest_vlan')),
            ('Connected Access Point', ('ap_count',)),
            ('Wired Guest', ('guest_count',)),
            ('Uplink Port 1', ('uplink_1', 'uplink_desc_a',)),
            ('Uplink Port 2', ('uplink_2', 'uplink_desc_b',)),
            ('Lag Interface', ('lag_name', 'lag_desc')),
        )

    device_name = StringVar(
        description="Device hostname (base name for stack)",
        label='Device Name'
    )
    switch_model = ObjectVar(
        description="Access switch model",
        model=DeviceType,
        label='Device Model'
    )
    site = ObjectVar(
        description="Choose Site name from drop-down",
        model=Site,
        label='Site Name'
    )
    mgmt_address = IPAddressWithMaskVar(
        description="Device Mgmt IP example: 192.168.20.10/23",
        label='Mgmt IP Address',
    )
    gateway_address = StringVar(
        description="Default Gateway. example: 10.10.10.1",
        label='Default Gateway',
    )
    is_stack_switch = BooleanVar(
        description="Is this a stack switch",
        default=False,
        label='Is Stack Switch',
    )
    stack_member_count = IntegerVar(
        description="Number of stack members (ignored if not a stack switch)",
        label='Stack Member Count',
        default=1,
        required=False,
        min_value=1,
        max_value=5,
    )
    mgmt_vlan = IntegerVar(
        description="Mgmt VLAN ID example: 60",
        label='Mgmt VLAN ID',
        default=60,
        min_value=2,
        max_value=4096,
    )
    blan_vlan = IntegerVar(
        description="Business LAN VLAN ID example: 1101",
        label='BLAN VLAN ID',
        min_value=2,
        max_value=4096,
    )
    guest_vlan = IntegerVar(
        description="Guest VLAN ID example: 3101",
        label='Guest VLAN ID',
        min_value=2,
        max_value=4096,
    )
    ap_count = IntegerVar(
        description="Number of access point to be install on the switch",
        label='AP Count',
        required=False,
        min_value=1,
        max_value=10,
    )
    guest_count = IntegerVar(
        description="Number of wired guest users that need access on the switch",
        label='Guest Count',
        required=False,
        min_value=1,
        max_value=10,
    )
    uplink_1 = ChoiceVar(
        choices=CHOICES,
        description="Uplink Interface drop-down",
        label='Uplink Interface',
    )
    uplink_desc_a = StringVar(
        description="Uplink Port 1 Interface Description",
        label='Uplink Interface Description',
        default='remotehost=os-z07-41ra0043-01-sw-lef-a; port=xe-0/0/18',
    )
    uplink_2 = ChoiceVar(
        choices=CHOICES,
        description="Uplink Interface drop-down",
        label='Uplink Interface',
    )
    uplink_desc_b = StringVar(
        description="Uplink Port 2 Interface Description",
        label='Uplink Interface Description',
        default='remotehost=os-z07-41ra0043-01-sw-lef-b; port=xe-0/0/18'
    )
    lag_name  = ChoiceVar(
        choices=LAG_CHOICES,
        description="Uplink Port 1/2 Lag Interface drop-down. example: Po1/ae1",
        label='Lag Interface Name',
        default='Po1',
    )
    lag_desc = StringVar(
        description="Uplink Port 1/2 Lag Interface description",
        label='Lag Interface Description',
        default='remotehost=os-z07-41ra0043-01-sw-lef-a/b; port=ae18'
    )
    
    def run(self, data, commit):
        switch_role = DeviceRole.objects.get(name='Access Switch')
        platform = Platform.objects.get(slug='ios')
        config_template = ConfigTemplate.objects.get(name='master_temp_acc_v1')
    
        # Determine stack count: 1 if not stack, or user-specified count if stack
        stack_count = data.get("stack_member_count") if data.get("is_stack_switch") else 1
        
        # Ensure stack_count is at least 1
        stack_count = max(1, int(data.get("stack_member_count", 1)))

        devices = []
        for i in range(1, stack_count + 1):
            # First device uses device_name, others use device_name + index
            if i == 1:
                name = data['device_name']
            else:
                name = f"{data['device_name']}{i}"
                
            switch = Device.objects.create(
                device_type=data['switch_model'],
                name=name,
                site=data['site'],
                status=DeviceStatusChoices.STATUS_ACTIVE,
                role=switch_role,
                platform=platform,
                config_template=config_template,
            )
            switch.custom_field_data["gateway"] = data["gateway_address"]
            switch.full_clean()
            switch.save()
            switch.refresh_from_db()
            devices.append(switch)
            self.log_success(f"Created switch: {switch.name} with {switch.interfaces.all().count()} interfaces")
        
        if data['is_stack_switch'] and (stack_count > 1):
            self.log_success(f"Stack creation complete. Total members: {len(devices)}")
            vc = VirtualChassis.objects.create(
                name=data['device_name'],
                description=data['device_name'],
            )
            for idx, device in enumerate(devices, start=1):
                pr = 16 - idx 
                add_member_to_vc(device, vc, idx, pr)
                if idx == 1:
                    vc.master = device
                    vc.save()
                    vc.refresh_from_db()
                device.refresh_from_db()

        for idx, device in enumerate(devices, start=1):
            if idx > 1:
                for intf in device.interfaces.all():
                    intf.name = replace_slot(intf.name, idx)
                    intf.save()
                
                device.refresh_from_db()
                self.log_success(f"Interface name has been updated for stack member {idx}")

        vlan_group = VLANGroup.objects.create(
                        name=data["device_name"],
                        slug=slugify(data["device_name"]),
                        scope_type=ContentType.objects.get_for_model(Site),
                        scope_id=data['site'].id,
                        description="vlan_grp",
                    )
        self.log_success(f"Created new vlan group: {vlan_group}")
        blan = VLAN.objects.create(
                        group=vlan_group,
                        vid=data["blan_vlan"],
                        name="blan",
                        status="active",
                        site=data['site'],
                        description="Business LAN",
                    )
        mgmt = VLAN.objects.create(
                group=vlan_group,
                vid=data["mgmt_vlan"],
                name="mgmt",
                status="active",
                site=data['site'],
                description="Mgmt Vlan",
            )
        guest = VLAN.objects.create(
                group=vlan_group,
                vid=data["guest_vlan"],
                name="guest",
                status="active",
                site=data['site'],
                description="Guest Vlan",
            )
        self.log_success(f"Created new vlans and added to group: VLANGroup: {vlan_group}, VLANs: {blan}:{mgmt}:{guest}")
        
        main_switch = devices[0]
        
        for idx, device in enumerate(devices, start=1): 
            if idx == 1:
                interface_portc = Interface.objects.create(
                    device=device, 
                    name=data["lag_name"], 
                    type="lag", 
                    description=data["lag_desc"],
                    mode='tagged'
                )
                interface_mgmt = Interface.objects.create(
                    device=device, 
                    name=f'vlan{str(data["mgmt_vlan"])}', 
                    type="virtual", 
                    description="mgmt interface",
                )
                if data['is_stack_switch'] and (stack_count > 1):
                    self.log_success(f"Created new Po1 and mgmt int vlan: {interface_mgmt}, Portchannel:{interface_portc} on member {idx}")
                else:
                    self.log_success(f"Created new Po1 and mgmt int vlan: {interface_mgmt}, Portchannel:{interface_portc}")
            
            elif idx == len(devices):            
                interface_portc = Interface.objects.create(
                device=device, 
                name=data["lag_name"], 
                type="lag", 
                description=data["lag_desc"],
                )   
                self.log_success(f"Created new Po1: Portchannel:{interface_portc} on member {idx}")
        
        mgmt_ip = IPAddress.objects.create(
            address=data['mgmt_address'],
            status="active",
            description=data["device_name"],
        )
        self.log_success(f"Created IP Address: Mgmt IP: {mgmt_ip}")
        
        mgmt_ip.assigned_object = interface_mgmt
        mgmt_ip.save()
        
        main_switch.primary_ip4 = mgmt_ip
        main_switch.save()
        self.log_success(f"Primary IPv4 address: {devices[0].primary_ip4.address} on {main_switch.name}")

        blan_user_port = []
        guest_user_port = []
        ap_port = []
        
        if data['is_stack_switch'] and (stack_count > 1):
            ap_count = per_switch_with_adding(data["ap_count"], len(devices))[0]
            guest_count = per_switch_with_adding(data["guest_count"], len(devices))[0]
        else:
            ap_count = data["ap_count"]
            guest_count = data["guest_count"]
        
        for idx, device in enumerate(devices, start=1):   
            usable_int = device.interfaces.filter(name__contains='/0/').reverse()
            blan_list, ap_list, guest_list = distribute_items(usable_int, ap_count, guest_count)
            blan_user_port.extend(blan_list)
            ap_port.extend(ap_list)
            guest_user_port.extend(guest_list)
                
            if data['is_stack_switch'] and (stack_count > 1):
                self.log_success(f"Port allocation: BLAN ports = {len(blan_list)}, AP ports = {len(ap_list)}, GUEST ports = {len(guest_list)} on stack member {idx}.")
            else:
                self.log_success(f"Port allocation: BLAN ports = {len(blan_list)}, AP ports = {len(ap_list)}, GUEST ports = {len(guest_list)}")
         
        self.log_success(f"Total ports — BLAN: {len(blan_user_port)}, GUEST: {len(guest_user_port)}, AP: {len(ap_port)}")
        
        if ap_port:
            for idx, ap_int in enumerate(ap_port, start=1):
                ap_int.mode = "tagged"
                ap_int.description = f"<<remotehost={main_switch}-wif-0{idx}>>"
                ap_int.untagged_vlan = blan
                ap_int.full_clean()
                ap_int.save()
                ap_int.tagged_vlans.add(blan,)
        
        if blan_user_port:            
            for b_int in blan_user_port:
                b_int.mode = "access"
                b_int.description = "<<remotehost=User>>"
                b_int.untagged_vlan = blan
                b_int.full_clean()
                b_int.save()
        
        if guest_user_port:
            for g_int in guest_user_port:
                g_int.mode = "access"
                g_int.description = "<<remotehost=User>>"
                g_int.untagged_vlan = guest
                g_int.full_clean()
                g_int.save()

        self.log_success("Updated all interfaces as required....................................")

        lag_int = main_switch.interfaces.get(name=data["lag_name"])
        lag_int.tagged_vlans.add(blan, mgmt, guest)
        lag_int.full_clean()
        lag_int.save()
        lag_int.refresh_from_db()
        self.log_success(f"Update interface Lag: {lag_int}")

        uplink1_int = main_switch.interfaces.get(name=data["uplink_1"])
        uplink1_int.mode = "tagged"
        uplink1_int.description = f"<<{data['uplink_desc_a']}>>"
        uplink1_int.lag = main_switch.interfaces.get(name=data["lag_name"])
        uplink1_int.full_clean()
        uplink1_int.save()
        
        uplink1_int.tagged_vlans.set([blan, mgmt, guest])
        uplink1_int.save()
        uplink1_int.refresh_from_db()

        if data['is_stack_switch'] and (stack_count > 1):
            self.log_success(f"Update uplink 1: {uplink1_int} tagged={list(uplink1_int.tagged_vlans.values_list('vid', flat=True))} on stack member 1")
        else:
            self.log_success(f"Update uplink 1: {uplink1_int} tagged={list(uplink1_int.tagged_vlans.values_list('vid', flat=True))}")

        if data['is_stack_switch'] and (stack_count > 1):
            new_int = replace_slot(data["uplink_2"], len(devices))
            uplink_new = to_one_ended(new_int)
            uplink2_int = devices[-1].interfaces.get(name=uplink_new)
        else:
            uplink2_int = devices[-1].interfaces.get(name=data["uplink_2"])

        uplink2_int.mode = "tagged"
        uplink2_int.description = f"<<{data['uplink_desc_b']}>>"
        uplink2_int.lag = devices[-1].interfaces.get(name=data["lag_name"])
        uplink2_int.full_clean()
        uplink2_int.save()
        
        uplink2_int.tagged_vlans.set([blan, mgmt, guest])
        uplink2_int.save()
        uplink2_int.refresh_from_db()
        
        if data['is_stack_switch'] and (stack_count > 1):
            self.log_success(f"Update uplink 2: {uplink2_int} tagged={list(uplink2_int.tagged_vlans.values_list('vid', flat=True))} on stack member {len(devices)}")
        else:
            self.log_success(f"Update uplink 2: {uplink2_int} tagged={list(uplink2_int.tagged_vlans.values_list('vid', flat=True))}")
            
