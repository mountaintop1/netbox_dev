from extras.scripts import *
from django.utils.text import slugify
from django.contrib.contenttypes.models import ContentType
from typing import Tuple

from dcim.choices import DeviceStatusChoices
from dcim.models import Device, DeviceRole, DeviceType, Site, Platform, Interface
from extras.models import ConfigTemplate


def instantiate_device_components_from_templates(device):
    dt = device.device_type

    # Console Ports
    for t in dt.consoleporttemplates.all():
        device.consoleports.get_or_create(
            name=t.name,
            defaults={
                "type": t.type,
                "label": t.label,
                "description": t.description,
            },
        )

    # Power Ports
    for t in dt.powerporttemplates.all():
        device.powerports.get_or_create(
            name=t.name,
            defaults={
                "type": t.type,
                "label": t.label,
                "maximum_draw": t.maximum_draw,
                "allocated_draw": t.allocated_draw,
                "description": t.description,
            },
        )

    # Interfaces (no mac_address on InterfaceTemplate in 4.4)
    for t in dt.interfacetemplates.all():
        device.interfaces.get_or_create(
            name=t.name,
            defaults={
                "type": t.type,
                "label": t.label,
                "mgmt_only": t.mgmt_only,
                "enabled": True,
                "description": t.description,
            },
        )

    # Rear Ports
    rear_map = {}
    for t in dt.rearporttemplates.all():
        rp, _ = device.rearports.get_or_create(
            name=t.name,
            defaults={
                "type": t.type,
                "label": t.label,
                "positions": t.positions,
                "description": t.description,
            },
        )
        rear_map[t.pk] = rp

    # Front Ports (link to rear)
    for t in dt.frontporttemplates.all():
        defaults = {
            "type": t.type,
            "label": t.label,
            "rear_port_position": t.rear_port_position,
            "description": t.description,
        }
        if getattr(t, "rear_port_id", None):
            defaults["rear_port"] = rear_map.get(t.rear_port_id)
        device.frontports.get_or_create(name=t.name, defaults=defaults)

    # Module Bays
    for t in dt.modulebaytemplates.all():
        device.modulebays.get_or_create(
            name=t.name,
            defaults={
                "label": t.label,
                "position": t.position,
                "description": t.description,
            },
        )

    # Power Outlets (link to power ports)
    pp_map = {
        ppt.pk: device.powerports.get(name=ppt.name)
        for ppt in dt.powerporttemplates.all()
        if device.powerports.filter(name=ppt.name).exists()
    }
    for t in dt.poweroutlettemplates.all():
        defaults = {
            "type": t.type,
            "label": t.label,
            "feed_leg": t.feed_leg,
            "description": t.description,
        }
        if getattr(t, "power_port_id", None):
            defaults["power_port"] = pp_map.get(t.power_port_id)
        device.poweroutlets.get_or_create(name=t.name, defaults=defaults)


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
        instantiate_device_components_from_templates(switch)
        switch.refresh_from_db()
        self.log_success(f"Created new switch: {switch} with {switch.interfaces.all().count()} interfaces")
