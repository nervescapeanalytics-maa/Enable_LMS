# Admin Template Override Manifest

**Generated:** Thu Feb 19 06:07:10 PM IST 2026
**Django Version:** 4.2.17
**Server:** nsmlapd13

This document tracks all customized Django admin templates.
Review after every Django upgrade to ensure compatibility.

---

## base_site.html

**Type:** Override of Django built-in template
**Django source:** `django/contrib/admin/templates/admin/base_site.html`

### Template Blocks Used

```
branding
extrahead
extrastyle
footer
nav
title
usertools
```

### Template Tags Loaded

```
static 
```

**Extends:** `admin/base.html`

### Custom Static Resources

```
https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap
https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css
/
/staff/dashboard/
/
/admin/
/admin/auth/user/
/admin/password_change/
/admin/accounts/admin/
/admin/accounts/role/
/admin/logout/
```

**Diff size:** ~132
0 lines changed from Django source

---

## index.html

**Type:** Override of Django built-in template
**Django source:** `django/contrib/admin/templates/admin/index.html`

### Template Blocks Used

```
content
title
```

### Template Tags Loaded

```
static 
```

**Extends:** `admin/base_site.html`

### Custom Static Resources

```
/admin/system_config/aifeatureconfig/
/admin/system_config/aifeatureconfig/add/
/admin/accounts/student/import-csv/
/admin/accounts/student/export-all-csv/
/admin/accounts/student/add/
/admin/accounts/teacher/add/
/admin/assessments/test/add/
/admin/classes/scheduledclass/add/
/admin/communication/announcement/add/
/admin/audit/auditlog/
/admin/system_config/attendancerule/
/admin/system_config/classlinkconfig/
/admin/accounts/role/
/admin/system_config/classlinkconfig/
/admin/classes/scheduledclass/
/admin/system_config/aifeatureconfig/
/admin/system_config/attendancerule/
/admin/accounts/role/
/admin/attendance/attendance/
/admin/accounts/student/
/admin/accounts/usergroup/
/admin/accounts/usergroup/
/admin/accounts/usergroup/add/
/admin/accounts/usergroup/{{ group.id }}/change/
#
#
#
#
#
#
/admin/accounts/usergroup/
/admin/system_config/integrationconfig/add/
/admin/system_config/integrationconfig/add/?integration_type=YOUTUBE
/admin/system_config/integrationconfig/add/?integration_type=LLM
/admin/system_config/classlinkconfig/add/
/admin/system_config/integrationconfig/add/?integration_type=STORAGE
/admin/system_config/featureflag/add/
/admin/system_config/aifeatureconfig/add/
/admin/system_config/reporttemplate/add/
/admin/system_config/reporttemplate/
/staff/reports/?report_type=attendance&date_range=today&format=excel
/staff/reports/?report_type=students&status=ACTIVE&format=excel
/staff/reports/?report_type=students&fee_status=PENDING&format=excel
/staff/reports/?report_type=attendance&date_range=month&format=pdf
/admin/system_config/reporttemplate/
/staff/reports/run/{{ template.id }}/
/admin/system_config/reporttemplate/{{ template.id }}/change/
/admin/system_config/reporttemplate/add/
```

**Diff size:** ~809
0 lines changed from Django source

---

## enhanced_change_list.html

**Type:** Custom template (no Django equivalent)
**Risk:** Low — Django upgrades won't conflict with this file

### Template Blocks Used

```
object
```

### Template Tags Loaded

```
static 
```

**Extends:** `admin/change_list.html`

### Custom Static Resources

```
import-csv/
export-all-csv/
```

---

## import_csv.html

**Type:** Custom template (no Django equivalent)
**Risk:** Low — Django upgrades won't conflict with this file

### Template Blocks Used

```
content
title
```

### Template Tags Loaded

```
static 
```

**Extends:** `admin/base_site.html`

### Custom Static Resources

```
../
```

---

## change_list.html

**Type:** Override of Django built-in template
**Django source:** `django/contrib/admin/templates/admin/change_list.html`

### Template Blocks Used

```
content
```

### Template Tags Loaded

```
i18n admin_urls 
```

**Extends:** `admin/change_list.html`

**Diff size:** ~98
0 lines changed from Django source

---

## login.html

**Type:** Override of Django built-in template
**Django source:** `django/contrib/admin/templates/admin/login.html`

### Template Blocks Used

```
bodyclass
content
content_title
extrastyle
nav
usertools
```

### Template Tags Loaded

```
i18n static 
```

**Extends:** `admin/base_site.html`

### Custom Static Resources

```
/
```

**Diff size:** ~509
0 lines changed from Django source

---

