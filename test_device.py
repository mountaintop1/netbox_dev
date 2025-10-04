from extras.scripts import *
from django.utils.text import slugify
from django.contrib.contenttypes.models import ContentType
from typing import Tuple

from dcim.choices import DeviceStatusChoices
from dcim.models import Device, DeviceRole, DeviceType, Site, Platform, Interface
from extras.models import ConfigTemplate




class DeviceOnboarding(Script):

    class Meta:
        name = "Device Onboarding"
        description = "Provision a New switch to Site"
        commit_default = False
    
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
    gateway_address = StringVar(
        description="Default Gateway. example: 10.10.10.1",
        label='Default Gateway',
    )

    uplink_sw_a = ObjectVar(
        description="First Uplink Dis/Leaf SW",
        model=Device,
        label='Uplink Dis/Leaf Switch A'
    )
    uplink_intf_sw_a = ObjectVar(
        description="All interfaces not connected",
        model=Interface,
        label='Uplink Switch A Interfaces',
        query_params={
            'device': '$uplink_sw_a'
        }
    )

    for iface in Interface.objects.filter(device=device, cable__isnull=True).order_by("name"):

    def run(self, data, commit):

        # Create access switches
        switch_role = DeviceRole.objects.get(name='Access Switch')
        platform = Platform.objects.get(slug='ios')

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
