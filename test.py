from extras.scripts import *
from dcim.models import Site

my_dynamic_choice = ChoiceVar(
    choices=[],
    description="Select a Site:",
    )


class MyCustomScript(Script):
    class Meta:
        name = "test 1"
        description = "Test dynamic var"
        commit_default = False

    def run(self, data, commit):
        site_choices = [(site.slug, site.name) for site in Site.objects.all()]
        data['my_dynamic_choice'] = site_choices
        
        selected_site_slug = data['my_dynamic_choice']
        selected_site = Site.objects.get(slug=selected_site_slug)
        
        self.log_info(f"Selected site: {selected_site.name}")

