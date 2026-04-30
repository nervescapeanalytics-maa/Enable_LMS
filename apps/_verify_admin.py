import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms_enterprise.settings')
django.setup()

from classes.admin import (
    YouTubeIntegrationAdminForm, ClassLinkConfigAdminForm, ScheduledClassAdminForm,
    IntegrationConfigProxyAdmin, ClassLinkConfigProxyAdmin, ScheduledClassAdmin,
    YouTubeChannelAdmin, ClassAccessTokenAdmin, ClassWatchTimeAdmin,
)
from django.contrib.admin.sites import site

print("=== Forms ===")
for f in [YouTubeIntegrationAdminForm, ClassLinkConfigAdminForm, ScheduledClassAdminForm]:
    print(f"  {f.__name__} OK")

print("\n=== Admin Registrations ===")
registered = {m.__name__: a.__class__.__name__ for m, a in site._registry.items() if m.__module__.startswith('classes')}
for m, a in sorted(registered.items()):
    print(f"  {m} -> {a}")

print("\n=== IntegrationConfigProxy fieldsets ===")
for name, opts in IntegrationConfigProxyAdmin.fieldsets:
    collapse = "(collapsed)" if "collapse" in opts.get("classes", ()) else ""
    print(f"  [{name}] {len(opts['fields'])} fields {collapse}")

print("\n=== ClassLinkConfig fieldsets ===")
for name, opts in ClassLinkConfigProxyAdmin.fieldsets:
    collapse = "(collapsed)" if "collapse" in opts.get("classes", ()) else ""
    print(f"  [{name}] {len(opts['fields'])} fields {collapse}")

print("\n=== ScheduledClass fieldsets ===")
for name, opts in ScheduledClassAdmin.fieldsets:
    collapse = "(collapsed)" if "collapse" in opts.get("classes", ()) else ""
    print(f"  [{name}] {len(opts['fields'])} fields {collapse}")

print("\n=== YouTubeChannel fieldsets ===")
for name, opts in YouTubeChannelAdmin.fieldsets:
    collapse = "(collapsed)" if "collapse" in opts.get("classes", ()) else ""
    print(f"  [{name}] {len(opts['fields'])} fields {collapse}")

# Count visible (non-collapsed) fields for each admin
for admin_name, admin_cls in [
    ("IntegrationConfigProxy", IntegrationConfigProxyAdmin),
    ("ClassLinkConfigProxy", ClassLinkConfigProxyAdmin),
    ("ScheduledClass", ScheduledClassAdmin),
    ("YouTubeChannel", YouTubeChannelAdmin),
]:
    visible = sum(len(opts["fields"]) for _, opts in admin_cls.fieldsets if "collapse" not in opts.get("classes", ()))
    total = sum(len(opts["fields"]) for _, opts in admin_cls.fieldsets)
    print(f"\n  {admin_name}: {visible} visible / {total} total fields")

print("\nAll checks passed!")
