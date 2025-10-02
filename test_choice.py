from django import forms
from extras.scripts import Script, ChoiceVar, ObjectVar
from dcim.models import DeviceType


class DynamicChioce(ChoiceVar):
  pass


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

class DynamicChioce(ChoiceVar):
    """
    A dynamic choice field that changes based on the selected switch model.
    """
    def __init__(self, *args, **kwargs):
        # Remove the choices parameter as we'll set them dynamically
        kwargs.pop('choices', None)
        super().__init__(*args, **kwargs)

    def prepare_kwargs(self, data, initial):
        kwargs = super().prepare_kwargs(data, initial)
        
        # Get the selected switch model from the form data
        switch_model = data.get('switch_model') if data else initial.get('switch_model')
        
        if switch_model:
            # Get the device type slug from the selected model
            if hasattr(switch_model, 'slug'):
                model_slug = switch_model.slug
            else:
                # If it's just the initial value (ID), we might need to fetch the object
                try:
                    device_type = DeviceType.objects.get(pk=switch_model)
                    model_slug = device_type.slug
                except (DeviceType.DoesNotExist, ValueError):
                    model_slug = None
            
            # Set the choices based on the model slug
            if model_slug and model_slug in CHOICES_BY_MODEL:
                kwargs['choices'] = CHOICES_BY_MODEL[model_slug]
            else:
                kwargs['choices'] = []  # Or provide a default empty choice
        else:
            kwargs['choices'] = []  # No model selected yet
        
        return kwargs
    
class DeviceDynamic(Script):

    class Meta:
        name = "Dynamic Choice Fields"
        description = "Testing Dynamic chioce f"
        commit_default = False

    switch_model = ObjectVar(
        description="Access switch model",
        model=DeviceType,
        label='Device Model',
        required=True
    )
    
    uplink_1 = DynamicChoiceVar(
        description="Uplink Interface drop-down",
        label='Uplink Interface',
    )

    def run(self, data, commit):
        self.log_info(f"Selected switch model: {data['switch_model']}")
        self.log_info(f"Selected uplink: {data['uplink_1']}")
        
        # Your script logic here
        return "Script completed successfully"
