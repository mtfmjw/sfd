SELECT grp.name group_name
	  ,perm.codename
	  ,content.app_label
	  ,content.model
  FROM auth_group grp
  left join auth_group_permissions grp_perm
  on grp_perm.group_id = grp.id
  left join auth_permission perm
  on perm.id = grp_perm.permission_id
  left join django_content_type content
  on content.id = perm.content_type_id
order by grp.name
;