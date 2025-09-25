from extras.scripts import *
from django.utils.text import slugify

from dcim.choices import DeviceStatusChoices
from dcim.models import Device, DeviceRole, DeviceType, Site, Platform, Interface, Manufacturer
from ipam.models import IPAddress, VLAN, VLANGroup


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
        choices=CHOICES,
        description="Uplink Interface drop-down",
        label='Uplink Interface'
    )
    uplink_desc_a = StringVar(
        description="Uplink Port 1 Interface Description",
        label='Uplink Interface Description',
        default='<<remotehost=os-z07-41ra0043-01-sw-lef-a; port=xe-0/0/18>>',
    )
    uplink_2 = ChoiceVar(
        choices=CHOICES,
        description="Uplink Interface drop-down",
        label='Uplink Interface'
    )
    uplink_desc_b = StringVar(
        description="Uplink Port 2 Interface Description",
        label='Uplink Interface Description',
        default='<<remotehost=os-z07-41ra0043-01-sw-lef-b; port=xe-0/0/18>>'
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
        default='<<remotehost=os-z07-41ra0043-01-sw-lef-a/b; port=ae18>>'
    )
    def run(self, data, commit):

        # Create access switches
        switch_role = DeviceRole.objects.get(name='Access Switch')
        platform = Platform.objects.get(slug='ios')
        dt = DeviceType.objects.get(part_number=data['switch_model'])
        mfr = dt.manufacturer
        switch = Device(
            device_type=data['switch_model'],
            name=data['device_name'],
            site=data['site'],
            status=DeviceStatusChoices.STATUS_ACTIVE,
            role=switch_role,
            platform=platform,
            config_template='master_temp_acc_v1',
            cf_gateway=data['gateway_address'],
            manufacturer=mfr,
        )
        switch.save()
        self.log_success(f"Created new switch: {switch} from {data}")

        # Generate a CSV table of new devices
        output = [
            'name,make,model'
        ]
        for device in Device.objects.filter(site=site):
            attrs = [
                device.name,
                device.device_type.manufacturer.name,
                device.device_type.model
            ]
            output.append(','.join(attrs))

        return '\n'.join(output)


name = "Suncor Custom Script"
