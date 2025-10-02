from django import forms
from extras.scripts import Script, ChoiceVar, ObjectVar
from dcim.models import DeviceType

# Your choices definitions (same as above)
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

    def clean(self):
        """
        Custom clean method to dynamically update choices based on switch model selection
        """
        cleaned_data = super().clean()
        
        switch_model = cleaned_data.get('switch_model')
        if switch_model:
            # Update the uplink_1 choices based on the selected model
            if hasattr(switch_model, 'slug') and switch_model.slug in CHOICES_BY_MODEL:
                self.fields['uplink_1'].choices = CHOICES_BY_MODEL[switch_model.slug]
            else:
                self.fields['uplink_1'].choices = []
        
        return cleaned_data

    def run(self, data, commit):
        self.log_info(f"Selected switch model: {data['switch_model']}")
        
        if data.get('uplink_1'):
            self.log_info(f"Selected uplink: {data['uplink_1']}")
        else:
            self.log_warning("No uplink interface selected")
        
        return "Script completed successfully"
