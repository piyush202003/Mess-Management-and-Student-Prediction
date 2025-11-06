3)before activating the environment first check if: Get-ExecutionPolicy
			if output of this command is "Restricted" then to remove it
				a)temporary:Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
				b)permanent:Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser


Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
cd ../env/Scripts
.\activate
cd ../../FinalYear
python manage.py runserver



online host
.\ngrok http 8000
.\ngrok config add-authtoken 2Q4xyhAqT3jDfExampleTokenXyZ_1AbCdEfgHiJ
.\ngrok config check
.\ngrok http 8000
then use this link=> https://ascocarpous-undelivered-lexie.ngrok-free.dev
