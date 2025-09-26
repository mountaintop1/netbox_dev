from extras.scripts import *
from django.utils.text import slugify
from django.contrib.contenttypes.models import ContentType

from dcim.choices import DeviceStatusChoices
from dcim.models import Device, DeviceRole, DeviceType, Site, Platform, Interface, Manufacturer
from ipam.models import IPAddress, VLAN, VLANGroup
from extras.models import ConfigTemplate


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

CHOICES = {
    "cisco-c9300l-24p-4x": choices1,
    "cisco-c9300l-48uxg-4x": choices1,
    "cisco-c9300lm-24u-4y": choices3,
    "cisco-c9200cx-12p-2x2g": choices2,
    "cisco-ie-4000-8gt8gp4g-e": choices4,
}

LAG_CHOICES = (
    ('Po1', 'Po1'),
    ('Po2', 'Po2'),
    ('Po3', 'Po3'),
)


class AddDevices(Script):

    class Meta:
        name = "Add New Device To Site"
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
        label='is_stack'
    )
    mgmt_vlan = IntegerVar(
        description="Mgmt VLAN ID example: 60",
        label='Mgmt VLAN ID',
        default=60
    )
    blan_vlan = IntegerVar(
        description="Business LAN VLAN ID example: 1101",
        label='BLAN VLAN ID'
    )
    guest_vlan = IntegerVar(
        description="Guest VLAN ID example: 3101",
        label='Guest VLAN ID'
    )
    ap_count = IntegerVar(
        description="Number of access point to be install on the switch",
        label='AP Count',
        required=False
    )
    guest_count = IntegerVar(
        description="Number of wired guest users that need access on the switch",
        label='Guest Count',
        required=False
    )
    uplink_1 = ChoiceVar(
        choices=lambda data: CHOICES_BY_MODEL.get(
            getattr(data.get("switch_model"), "slug", None),  # use slug key
            ()
        ),
        description="Uplink Interface drop-down",
        label='Uplink Interface'
    )
    uplink_desc_a = StringVar(
        description="Uplink Port 1 Interface Description",
        label='Uplink Interface Description',
        default='remotehost=os-z07-41ra0043-01-sw-lef-a; port=xe-0/0/18',
    )
    uplink_2 = ChoiceVar(
        choices=lambda data: CHOICES_BY_MODEL.get(
            getattr(data.get("switch_model"), "slug", None),  # use slug key
            ()
        ),
        description="Uplink Interface drop-down",
        label='Uplink Interface'
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
        dt = data["switch_model"]                 # DeviceType instance
        selected1 = data["uplink_1"]               # the chosen value from the dynamic list
        selected2 = data["uplink_2"]
        self.log_success(f"Model: {dt.slug} ({dt.model}), uplink_1: {selected1}, uplink_2: {selected2}")
        
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
            name=str(data["mgmt_vlan"]), 
            type="virtual", 
            description="mgmt",
            mode='tagged'
        )
        self.log_success(f"Created new Po1 and mgmt int vlan: VLAN{interface_mgmt}, Portchannel:{interface_portc}")

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
        


name = "Suncor Custom Script"
