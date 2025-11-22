
# Mess Attendance Prediction and Dish Recommendation System

This project is a Django-based web application that predicts student attendance for mess providers and recommends dishes based on historical attendance data. It uses machine learning models trained on attendance and menu data to provide intelligent predictions and recommendations.

---

## Features

- Train and retrain attendance prediction models per provider
- Predict student attendance for specific meals and dishes
- Recommend top dishes likely to attract students
- Analytics dashboard showing recent predictions and model performance
- Debug tools for data inspection

---

## Setup and Running the Project

### Activate virtual environment and run server

Install vertual env and install updated python, Django, torch, matplotlib, scikit-learn and other libraries

On Windows PowerShell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
cd ../env/Scripts
.\activate
cd ../../FinalYear

Run development server
python manage.py runserver

### Running the project on an online host (using ngrok)

.\ngrok config add-authtoken 2Q4xyhAqT3jDfExampleTokenXyZ_1AbCdEfgHiJ
.\ngrok config check
.\ngrok http 8000


Once ngrok is running, you can access your application on the internet using the generated URL, for example:

[https://ascocarpous-undelivered-lexie.ngrok-free.dev](https://ascocarpous-undelivered-lexie.ngrok-free.dev)

---

## Project Structure

- `mess_app/` - Contains main app with views for prediction, recommendation, training, and analytics
- `ml/provider_model.py` - Machine learning model classes and helper functions
- `accounts/`, `provider/`, `student/` - Apps managing users, menus, and attendance respectively
- Templates and static files for frontend UI rendering

---

## Additional Information

- Requires Python 3.x and Django >= 4.x
- Requires additional libraries: scikit-learn, pandas, numpy, etc.
- Machine learning models stored per provider for individualized predictions
- Logs and error handling included for ease of debugging

---

Feel free to customize the auth token and URL placeholders for your environment.

## Logins
- There are two logins student and mess provider
- For creating new account use valid email Id for OTP validation

## Mess Provider
- Can acess all subscribed students and see there attendance 
- From home page provider can start mess and end it for lunch and dinner mess can be started befor 2 hr of setted time and can end before or will end automatically 2 hr later of end time

## Mess Dashboard
- Here all graphs and analysis part all for more accuret prediction provider must ReTrain the model after some time

## All requirements are given in PPT


