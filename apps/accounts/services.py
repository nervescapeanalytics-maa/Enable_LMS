"""
RBAC Service Layer
Business logic for Role-Based Access Control.
When a role is assigned, the user inherits all permissions
associated with that role, including parent role permissions.
"""
from django.db.models import Q


class RBACService:
    """Service for role-based access control operations."""

    def __init__(self, repository=None):
        self.repository = repository or RBACRepository()

    def get_role_permissions(self, role):
        """
        Get all permissions for a role, including inherited from parent roles.
        Walks up the hierarchy chain.
        """
        from accounts.models import RolePermission

        permissions = set()
        visited = set()
        current_role = role

        while current_role and current_role.pk not in visited:
            visited.add(current_role.pk)
            role_perms = RolePermission.objects.filter(
                role=current_role
            ).select_related('permission')
            for rp in role_perms:
                permissions.add(rp.permission)
            current_role = current_role.parent_role

        return list(permissions)

    def assign_role_to_user(self, user_obj, role):
        """
        Assign a role to a user. The user inherits all permissions
        and dashboard privileges associated with that role.
        """
        from accounts.models import Admin as AdminUser

        if isinstance(user_obj, AdminUser):
            user_obj.role = role
            user_obj.save(update_fields=['role'])

        return self.get_role_permissions(role)

    def check_permission(self, role, permission_code):
        """Check if a role (including inherited) has a specific permission."""
        permissions = self.get_role_permissions(role)
        return any(p.code == permission_code for p in permissions)

    def get_user_permissions(self, admin_user):
        """Get all effective permissions for an admin user."""
        permissions = []
        if admin_user.role:
            permissions = self.get_role_permissions(admin_user.role)

        # Apply overrides
        overrides = admin_user.permissions_override or []
        if overrides:
            from accounts.models import Permission
            override_perms = Permission.objects.filter(code__in=overrides)
            perm_set = set(p.pk for p in permissions)
            for op in override_perms:
                if op.pk not in perm_set:
                    permissions.append(op)

        return permissions

    def get_dashboard_privileges(self, role):
        """
        Determine dashboard access based on role.
        Returns dict of module access.
        """
        permissions = self.get_role_permissions(role)
        modules = set()
        for perm in permissions:
            modules.add(perm.module)

        privilege_map = {
            'student': 'student' in modules,
            'teacher': 'teacher' in modules,
            'class': 'class' in modules,
            'assessment': 'assessment' in modules,
            'attendance': 'attendance' in modules,
            'material': 'material' in modules,
            'communication': 'communication' in modules,
            'audit': 'audit' in modules,
            'system': 'system' in modules,
            'tenant': 'tenant' in modules,
        }
        return privilege_map

    def create_default_roles(self, tenant):
        """Create default system roles for a new tenant."""
        from accounts.models import Role

        defaults = [
            {
                'code': 'SUPER_ADMIN',
                'name': 'Super Administrator',
                'role_type': 'SYSTEM',
                'applies_to': 'ADMIN',
                'level': 100,
            },
            {
                'code': 'TENANT_ADMIN',
                'name': 'Tenant Administrator',
                'role_type': 'TENANT_DEFAULT',
                'applies_to': 'ADMIN',
                'level': 90,
            },
            {
                'code': 'ACADEMIC_ADMIN',
                'name': 'Academic Administrator',
                'role_type': 'TENANT_DEFAULT',
                'applies_to': 'ADMIN',
                'level': 80,
            },
            {
                'code': 'TEACHER',
                'name': 'Teacher',
                'role_type': 'TENANT_DEFAULT',
                'applies_to': 'TEACHER',
                'level': 50,
            },
            {
                'code': 'STUDENT',
                'name': 'Student',
                'role_type': 'TENANT_DEFAULT',
                'applies_to': 'STUDENT',
                'level': 10,
            },
            {
                'code': 'PARENT',
                'name': 'Parent / Guardian',
                'role_type': 'TENANT_DEFAULT',
                'applies_to': 'PARENT',
                'level': 5,
            },
        ]

        created = []
        for role_data in defaults:
            role, was_created = Role.objects.get_or_create(
                tenant=tenant,
                code=role_data['code'],
                defaults=role_data,
            )
            if was_created:
                created.append(role)

        return created


class RBACRepository:
    """Data access layer for RBAC models."""

    def get_role_by_code(self, tenant_id, code):
        from accounts.models import Role
        return Role.objects.filter(
            tenant_id=tenant_id,
            code=code,
            is_active=True,
        ).first()

    def get_active_roles(self, tenant_id):
        from accounts.models import Role
        return Role.objects.filter(
            Q(tenant_id=tenant_id) | Q(tenant__isnull=True),
            is_active=True,
        ).order_by('-level')

    def get_permissions_for_module(self, module):
        from accounts.models import Permission
        return Permission.objects.filter(
            module=module,
            is_active=True,
        ).order_by('category', 'action')
