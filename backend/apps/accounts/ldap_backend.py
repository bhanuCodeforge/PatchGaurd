try:
    import ldap
except ImportError:
    ldap = None
from django.conf import settings
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class LDAPBackend:
    def authenticate(self, request, username=None, password=None, **kwargs):
        if ldap is None:
            return None  # python-ldap not installed, skip silently

        if not username or not password:
            return None

        # These would ideally be fetched from settings, allowing safe fallbacks
        ldap_uri = getattr(settings, 'LDAP_URI', '')
        bind_dn_template = getattr(settings, 'LDAP_BIND_DN_TEMPLATE', '')
        search_base = getattr(settings, 'LDAP_SEARCH_BASE', '')
        
        if not ldap_uri:
            logger.warning("LDAP_URI not configured.")
            return None

        conn = None
        try:
            conn = ldap.initialize(ldap_uri)
            conn.set_option(ldap.OPT_REFERRALS, 0)
            conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 10.0)

            bind_dn = bind_dn_template % username
            conn.simple_bind_s(bind_dn, password)

            # Search user attributes
            search_filter = f"(sAMAccountName={username})"
            result_id = conn.search(search_base, ldap.SCOPE_SUBTREE, search_filter, ['cn', 'mail', 'givenName', 'sn', 'memberOf'])
            result_type, result_data = conn.result(result_id, 0)
            
            if not result_data:
                return None
                
            dn, attrs = result_data[0]
            
            # Extract attributes safely
            email = attrs.get('mail', [b''])[0].decode('utf-8')
            first_name = attrs.get('givenName', [b''])[0].decode('utf-8')
            last_name = attrs.get('sn', [b''])[0].decode('utf-8')
            member_of = attrs.get('memberOf', [])

            role = self._map_groups_to_role(member_of)

            user, created = User.objects.update_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': role,
                    'is_ldap_user': True,
                    'ldap_dn': dn,
                    'must_change_password': False
                }
            )
            return user
            
        except ldap.INVALID_CREDENTIALS:
            logger.info(f"LDAP Invalid credentials for user {username}")
            return None
        except ldap.LDAPError as e:
            logger.error(f"LDAP Error: {e}")
            return None
        finally:
            if conn is not None:
                try:
                    conn.unbind_s()
                except Exception:
                    pass

    def _map_groups_to_role(self, member_of: list) -> str:
        admin_group = getattr(settings, 'LDAP_ADMIN_GROUP', 'PatchMgr-Admins')
        operator_group = getattr(settings, 'LDAP_OPERATOR_GROUP', 'PatchMgr-Operators')
        
        for group_dn_bytes in member_of:
            group_dn = group_dn_bytes.decode('utf-8')
            # very naive extraction, e.g. CN=AdminGroup,OU=Groups...
            cn_part = group_dn.split(',')[0]
            if cn_part.upper().startswith('CN='):
                cn = cn_part[3:]
                if cn == admin_group:
                    return 'admin'
                if cn == operator_group:
                    return 'operator'
        
        return 'viewer'

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
