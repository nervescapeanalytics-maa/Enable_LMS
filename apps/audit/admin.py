"""
Audit admin registrations moved to accounts/admin.py (User Account section).
All audit models are now managed via proxy models under the unified
'User Account' admin section for centralized access control management.
"""
# Models: AuditLog, AuditPurgePolicy, BackupPolicy, BackupHistory
# Registered as proxy models: AuditEntry, RetentionPolicy,
# BackupPolicyProxy, BackupRecord — see accounts/admin.py
