from django import forms
from extras.scripts import Script, ChoiceVar, ObjectVar
from dcim.models import DeviceType

# Define your choices
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

class DeviceDynamic(Script):
    class Meta:
        name = "Dynamic Choice Fields"
        description = "Testing Dynamic choice fields"
        commit_default = False

    switch_model = ObjectVar(
        description="Access switch model",
        model=DeviceType,
        label='Device Model',
        required=True
    )
    
    uplink_1 = ChoiceVar(
        choices=[],  # Will be populated dynamically
        description="Uplink Interface drop-down",
        label='Uplink Interface',
        required=False
    )

    def prepare_ui_form(self, form):
        """
        This method is called when preparing the form for display in the UI
        """
        # Get the current value of switch_model from the form
        switch_model = form.initial.get('switch_model')
        
        if switch_model:
            # Get the device type slug
            if hasattr(switch_model, 'slug'):
                model_slug = switch_model.slug
            else:
                try:
                    device_type = DeviceType.objects.get(pk=switch_model)
                    model_slug = device_type.slug
                except (DeviceType.DoesNotExist, ValueError):
                    model_slug = None
            
            # Update the choices for uplink_1 based on the model
            if model_slug and model_slug in CHOICES_BY_MODEL:
                form.fields['uplink_1'].choices = CHOICES_BY_MODEL[model_slug]
            else:
                form.fields['uplink_1'].choices = []
        
        return form

    def run(self, data, commit):
        self.log_info(f"Selected switch model: {data['switch_model']}")
        
        if data.get('uplink_1'):
            self.log_info(f"Selected uplink: {data['uplink_1']}")
        else:
            self.log_warning("No uplink interface selected")
        
        return "Script completed successfully"
