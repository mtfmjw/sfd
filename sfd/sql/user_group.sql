SELECT usr.last_login
      ,usr.is_superuser
      ,usr.username
      ,usr.first_name
      ,usr.last_name
      ,usr.email
      ,usr.is_staff
      ,usr.is_active
      ,usr.date_joined
	    ,grp.name
  FROM auth_user usr
  left join auth_user_groups usr_grp
  on usr_grp.user_id = usr.id
  left join auth_group grp
  on grp.id = usr_grp.group_id
where usr.username != 'admin'
order by usr.username;
