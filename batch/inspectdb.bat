echo off

setlocal enabledelayedexpansion
call %~dp0parameters


pushd %base_dir%

chcp 65001

::python manage.py inspectdb mcd_invoice_detail --database=default >%app_label%/models/invoice.py
::python manage.py inspectdb mcd_work_date --database=default >%app_label%/models/work_date.py
::python manage.py inspectdb mcd_sp_ac_customer_manage --database=default >%app_label%/models/customer.py
::python manage.py inspectdb mcd_sp_ac_contract_manage --database=default >%app_label%/models/contract.py
::python manage.py inspectdb mcd_sp_detail --database=default >%app_label%/models/contract_item.py
::python manage.py inspectdb mcd_sp_ac_convert --database=default >%app_label%/models/convert.py
::python manage.py inspectdb mcd_sp_ac_initialcost --database=default >%app_label%/models/initial_deploy.py
::python manage.py inspectdb mcd_sp_ac_it_subsidy --database=default >%app_label%/models/it_subsidy.py
::python manage.py inspectdb mcd_sp_ac_support --database=default >%app_label%/models/maintenance.py
::python manage.py inspectdb mcd_sp_ac_campaign --database=default >%app_label%/models/campain.py
::python manage.py inspectdb MCD_SP_MST_SUPPORT --database=default >%app_label%/models/support_master.py
::python manage.py inspectdb MCD_ERROR_LOG --database=default >%app_label%/models/error_log.py
::python manage.py inspectdb MCD_RESULT_SAVE --database=default >%app_label%/models/result_save.py

::python manage.py inspectdb MCD_SP_AC_USER --database=default >%app_label%/models/user.py
::python manage.py inspectdb MCD_SP_AC_ROLES --database=default >%app_label%/models/role.py
::python manage.py inspectdb MCD_SP_AC_USERS_ROLE --database=default >%app_label%/models/users_role.py
::python manage.py inspectdb MCD_SP_MST_SECTION --database=default >%app_label%/models/section.py
::python manage.py inspectdb MCD_SP_MST_AGENCY --database=default >%app_label%/models/agency.py

::python manage.py inspectdb WK_BCP_RENKEI_COMPANY --database=default >%app_label%/models/bcp_company.py
::python manage.py inspectdb WK_BCP_RENKEI_CONTRACT --database=default >%app_label%/models/bcp_contract.py
::python manage.py inspectdb WK_BCP_RENKEI_INITIAL --database=default >%app_label%/models/bcp_initial.py
::python manage.py inspectdb WK_BCP_RENKEI_ITEM --database=default >%app_label%/models/bcp_item.py
::python manage.py inspectdb WK_BCP_RENKEI_SUPPORT --database=default >%app_label%/models/bcp_support.py

popd
