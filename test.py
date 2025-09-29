from netbox.scripts import Script, ChoiceVar
from dcim.models import Site

class MyCustomScript(Script):
    class Meta:
        name = "test 1"
        description = "Test dynamic var"
        commit_default = False
    
    my_dynamic_choice = ChoiceVar(
        description="Select a Site:",
        choices=[],
    )

    def run(self, data, commit):
        pass
