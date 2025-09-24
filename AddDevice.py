from extras.scripts import *
from django.utils.text import slugify

from dcim.choices import DeviceStatusChoices, SiteStatusChoices
from dcim.models import Device, DeviceRole, DeviceType, Site

CHOICES = (
    ('n', 'North'),
    ('s', 'South'),
    ('e', 'East'),
    ('w', 'West')
)

class AddDevices(Script):

    class Meta:
        name = "Add New Devices"
        description = "Provision a new switch"
        fieldsets = (
            ('Device Object', ('device_name', 'switch_model', 'mgmt_address', 'gateway_address', 'is_stack_switch')),
            ('Site Object', ('site', 'mgmt_vlan', 'blan_vlan', 'guest_vlan')),
            ('Uplink Side A', ('remote_sw_name_a',)),
            ('Uplink Side B', ('remote_sw_name_b',)),
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
        description="Site name",
        model=Site,
        label='Site'
    )
    mgmt_address = IPAddressVar(
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
    )
    blan_vlan = IntegerVar(
        description="Business LAN VLAN ID example: 1101",
        label='BLAN VLAN ID'
    )
    guest_vlan = IntegerVar(
        description="Guest VLAN ID example: 3101",
        label='Guest VLAN ID'
    )
    remote_sw_name_a = ChoiceVar(choices=CHOICES)
    remote_sw_name_b = MultiChoiceVar(choices=CHOICES)

    def run(self, data, commit):

        # Create the new site
        site = Site(
            name=data['site_name'],
            slug=slugify(data['site_name']),
            status=SiteStatusChoices.STATUS_PLANNED
        )
        site.save()
        self.log_success(f"Created new site: {site}")

        # Create access switches
        switch_role = DeviceRole.objects.get(name='Access Switch')
        for i in range(1, data['switch_count'] + 1):
            switch = Device(
                device_type=data['switch_model'],
                name=f'{site.slug.upper()}-SW-{i}',
                site=site,
                status=DeviceStatusChoices.STATUS_PLANNED,
                role=switch_role
            )
            switch.save()
            self.log_success(f"Created new switch: {switch}")

        # Create routers
        router_role = DeviceRole.objects.get(name='WAN Router')
        for i in range(1, data['router_count'] + 1):
            router = Device(
                device_type=data['router_model'],
                name=f'{site.slug.upper()}-RTR-{i}',
                site=site,
                status=DeviceStatusChoices.STATUS_PLANNED,
                role=router_role
            )
            router.save()
            self.log_success(f"Created new router: {router}")

        # Create APs
        ap_role = DeviceRole.objects.get(name='Wireless AP')
        for i in range(1, data['ap_count'] + 1):
            ap = Device(
                device_type=data['ap_model'],
                name=f'{site.slug.upper()}-AP-{i}',
                site=site,
                status=DeviceStatusChoices.STATUS_PLANNED,
                role=ap_role
            )
            ap.save()
            self.log_success(f"Created new AP: {router}")
        
        # Create Servers
        server_role = DeviceRole.objects.get(name='vSphere')
        for i in range(1, data['server_count'] + 1):
            server = Device(
                device_type=data['server_model'],
                name=f'{site.slug.upper()}-VSP-{i}',
                site=site,
                status=DeviceStatusChoices.STATUS_PLANNED,
                role=server_role
            )
            server.save()
            self.log_success(f"Created new server: {router}")

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
