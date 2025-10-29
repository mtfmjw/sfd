echo off

pushd %~dp0..

cd %~dp0
cd ..
set base_dir=%cd%
popd
echo Base Directory: %base_dir%

set project=sfd_prj
set app_label=sfd

echo Current app: %app_label%

set database=postgres

