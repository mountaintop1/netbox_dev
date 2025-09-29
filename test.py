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
        required=True
    )

    def run(self, data, commit):
        site_choices = [(site.slug, site.name) for site in Site.objects.all()]
        self.my_dynamic_choice.choices = site_choices
        
        selected_site_slug = data['my_dynamic_choice']
        selected_site = Site.objects.get(slug=selected_site_slug)
        
        self.log_info(f"Selected site: {selected_site.name}")
