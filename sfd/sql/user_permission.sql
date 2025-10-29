SELECT usr.last_login
      ,usr.is_superuser
      ,usr.username
      ,usr.first_name
      ,usr.last_name
      ,usr.email
      ,usr.is_staff
      ,usr.is_active
      ,usr.date_joined
	  ,perm.codename
	  ,content.app_label
	  ,content.model
  FROM auth_user usr
  left join auth_user_user_permissions usr_perm
  on usr_perm.user_id = usr.id
  left join auth_permission perm
  on perm.id = usr_perm.permission_id
  left join django_content_type content
  on content.id = perm.content_type_id
where usr.username != 'admin'
order by usr.username;
