import os
from pydantic import BaseModel
from fastapi import FastAPI, Query, Depends, HTTPException, status, Request
import sqlalchemy
from sqlalchemy import create_engine
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from typing import Optional

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

from passlib.context import CryptContext

app = FastAPI()

host = os.environ['HOST']
user = os.environ['USER']
password = os.environ['PASSWORD']
database = os.environ['DATABASE']
port = os.environ['PORT']
SECRET_KEY = os.environ['HASH']
ALGORITHM = os.environ['ALGORITHM']
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ['TIMEOUT'])


ssl_args = {'ssl_ca': 'BaltimoreCyberTrustRoot.crt.pem'}
engine = create_engine('mysql+pymysql://{}:{}@{}/{}?ssl=true'.format(user, password, host, database),
                       connect_args=ssl_args)

tags_metadata = [
    {"name": "user", "description": "Handle User Operation"},
    {"name": "blood", "description": "Handle Queries Related to Blood"},
    {"name": "oxygen", "description": "Handle Queries Related to Oxygen"}
]


class Blood(BaseModel):
    mobileNumber: str
    bloodReceiver: bool
    bloodType: int
    hospitalName: str
    pickUpDrop: bool
    documentURI: str
    recoveryDate: str
    distanceWillingToTravel: int
    detailsAvailable: bool
    latitude: float
    longitude: float


class Oxygen(BaseModel):
    mobileNumber: str = Query(...)
    oxygenReceiver: bool = Query(...)
    hospitalName: str = Query(...)
    fullGear: bool = Query(...)
    canDeliver: bool = Query(...)
    oxygenDetailsAvailable: bool = Query(...)
    latitude: float
    longitude: float


class BloodReceive(BaseModel):
    mobileNumber: str = Query(...)
    bloodMessage: str = Query(...)
    latitude: float = Query(...)
    longitude: float = Query(...)


class OxygenReceive(BaseModel):
    mobileNumber: str = Query(...)
    oxygenMessage: str = Query(...)
    latitude: float = Query(...)
    longitude: float = Query(...)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str


class NewUser(BaseModel):
    name: str = Query(...)
    email: str = Query(...)
    location: str = Query(...)
    gender: bool = Query(...)
    age: int = Query(...)
    mobileNumber: str = Query(...)
    password: str = Query(...)


class UnicornException(Exception):
    def __init__(self, name: str):
        self.name = name


class resetPassword(BaseModel):
    mobileNumber: str = Query(...)
    password: str = Query(...)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

bloodList = [
    (0, 1, 2, 3),
    (1, 3),
    (2, 3),
    (3),
    (2, 3, 4, 5),
    (5, 3),
    (0, 1, 2, 3, 4, 5, 6, 7),
    (1, 3, 5, 7)
]

bloodMap = ['A+', 'A-', 'O+', 'O-', 'B+', 'B-', 'AB+', 'AB-']

app = FastAPI(
    title="COVAID Backend",
    description="Backend for COVAID",
    openapi_tags=tags_metadata,
    version="0.1.0",
    openapi_url="/api/v0.1.0/openapi.json",
    docs_url="/",
    redoc_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(conn, username: str):
    query = '''SELECT password, isdisabled FROM users WHERE mobileNumber = '{}' LIMIT 1'''.format(username)
    values = conn.execute(query)
    details = {
        'username': username
    }
    for value in values:
        details['hashed_password'] = value[0]
        details['disabled'] = bool(value[1])

    return details


def authenticate_user(conn, username: str, password: str):
    user = get_user(conn, username)
    print(user)

    if not user:
        return False

    if not verify_password(password, user['hashed_password']):
        return False

    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    with engine.connect() as conn:
        user = get_user(conn, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user['disabled']:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.exception_handler(UnicornException)
async def unicorn_exception_handler(request: Request, exc: UnicornException):
    return JSONResponse(
        status_code=418,
        content={
            "message": f"Oops! {exc.name}. There goes a rainbow..."
        },
    )


@app.post('/user/register',
          tags=["user"])
def register_new_user(new_user: NewUser):
    hashed_password = get_password_hash(new_user.password)

    with engine.connect() as conn:
        print("Gel")
        query = '''INSERT INTO users(email, location, gender, age, mobileNumber, password, name) 
        VALUES ('{0}','{1}', {2}, {3}, '{4}', '{5}', '{6}' )
        '''.format(new_user.email, new_user.location, new_user.gender, new_user.age, new_user.mobileNumber,
                   hashed_password, new_user.name)
        try:
            res = conn.execute(query)
            print(res)


            return {
                'message': "OK"
            }
        except Exception as E:
            print(E)
            return {
                'status': "400"
            }


@app.post("/user/login", response_model=Token,
          tags=["user"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    with engine.connect() as conn:
        user = authenticate_user(conn, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user['username']}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}


@app.get('/profile/{mobileNumber}',
         tags=["user"])
def get_profile(mobileNumber: str):
    with engine.connect() as conn:
        query = ''' SELECT name, email, location, gender, age, mobileNumber, createdAt as registerdOn
        FROM users WHERE mobileNumber = '{}'
        '''.format(mobileNumber)

        result = conn.execute(query)
        for value in result:
            return value


@app.post('/blood/entry',
          tags=["blood"])
async def blood_entry(blood: Blood):
    with engine.connect() as conn:
        recoveryDate = blood.recoveryDate.split('T')[0] + " 00:00:00"
        query = '''INSERT INTO bloodInfo(mobileNumber, bloodReceiver, bloodType, hospitalName, pickUpDrop, documentURI, 
        recoveryDate, distanceWillingToTravel, detailsAvailable, latitude, longitude, createdAt, updatedAt) 
        VALUES 
        ('{0}',{1},{2},'{3}',{4},'{5}','{6}',{7},{8},{9},{10}, now(), now())'''.format(blood.mobileNumber,
                                                                                       blood.bloodReceiver,
                                                                                       blood.bloodType,
                                                                                       blood.hospitalName,
                                                                                       blood.pickUpDrop,
                                                                                       blood.documentURI,
                                                                                       recoveryDate,
                                                                                       blood.distanceWillingToTravel,
                                                                                       blood.detailsAvailable,
                                                                                       blood.latitude,
                                                                                       blood.longitude)

        try:
            conn.execute(query)
            return {
                "message": "Processed"
            }
        except:
            return {
                "message": "User Role Already Exist"
            }


@app.post('/oxygen/entry',
          tags=["oxygen"])
async def oxygen_entry(oxygen: Oxygen):
    with engine.connect() as conn:
        query = '''INSERT INTO oxygenInfo(mobileNumber, oxygenReceiver, hospitalName, fullGear, canDeliver, 
                detailsAvailable, latitude, longitude, createdAt, updatedAt) 
                values ('{0}',{1},'{2}',{3},{4},{5},{6},{7},now(), now())'''.format(oxygen.mobileNumber,
                                                                                    oxygen.oxygenReciever,
                                                                                    oxygen.hospitalName,
                                                                                    oxygen.fullGear,
                                                                                    oxygen.canDeliver,
                                                                                    oxygen.oxygenDetailsAvailable,
                                                                                    oxygen.latitude, oxygen.longitude)

        try:
            conn.execute(query)
            return {
                "message": "Processed"
            }
        except:
            return {
                "message": "User Role Already Exist"
            }


@app.get('/blood/{mobileNumber}',
         tags=["blood"])
async def blood_get(mobileNumber: str):
    with engine.connect() as conn:
        query = '''SELECT * FROM bloodInfo WHERE mobileNumber = '{}' '''.format(mobileNumber)
        values = conn.execute(query)

        for value in values:
            return value

        return {
            'status': 400
        }


@app.get('/oxygen/{mobileNumber}',
         tags=["oxygen"])
async def oxygen_get(mobileNumber: str):
    with engine.connect() as conn:
        query = '''SELECT * FROM oxygenInfo WHERE mobileNumber = '{}' '''.format(mobileNumber)
        values = conn.execute(query)

        for value in values:
            return value

        return {
            'status': 400
        }


@app.post('/blood/receive/',
          tags=["blood"])
async def blood_receive_request(bloodreceive: BloodReceive):
    with engine.connect() as conn:
        query0 = '''SELECT bloodType FROM bloodInfo WHERE mobileNumber = '{}' '''.format(bloodreceive.mobileNumber)
        bt = conn.execute(query0)
        bg = None
        for i in bt:
            bg = i[0]

        query = ''' SELECT mobileNumber, ( 6371 * acos( cos( radians({0}) ) * cos( radians( latitude ) )
                * cos( radians( longitude ) - radians({1}) ) + sin( radians({2}) ) * sin(radians(latitude)) ) ) 
                AS distance
                FROM bloodInfo 
                WHERE bloodReceiver = 0 AND isActive = 1 AND bloodType in {3}
                HAVING distance < 500
                ORDER BY distance
                LIMIT 0 , 3;'''.format(bloodreceive.latitude, bloodreceive.longitude, bloodreceive.latitude,
                                       bloodList[bg])

        values = conn.execute(query)
        k = 0
        for value in values:
            query2 = ''' INSERT INTO bloodMapping(receiver, donor, distance) VALUES ('{}','{}',{})
            '''.format(bloodreceive.mobileNumber, value[0], value[1])
            conn.execute(query2)
            k += 1

        if k == 0:
            pass
        else:
            query3 = '''INSERT INTO customMessage(mobileNumber, message, contentType) 
                    VALUES('{0}','{1}',0)
                    '''.format(bloodreceive.mobileNumber, bloodreceive.bloodMessage)
            conn.execute(query3)

        return {
            "userNotified": k
        }


@app.get('/blood/donate/{mobileNumber}',
         tags=["blood"])
async def blood_receive_data(mobileNumber: str):
    with engine.connect() as conn:
        query0 = ''' SELECT bI.bloodType, bI.hospitalName, bI.pickUpDrop, bI.documentURI, bM.donor, bM.receiver,
        bM.distance, bM.isAccepted 
        FROM bloodInfo as bI, bloodMapping as bM 
        WHERE bM.donor = '{}' AND bM.isAccepted = 1 and bI.mobileNumber = bM.receiver
        '''.format(mobileNumber)
        values = conn.execute(query0)
        for value in values:
            value = dict(value)
            value['bloodType'] = bloodMap[value['bloodType']]
            return [value]

        query = '''SELECT bI.mobileNumber, bI.bloodType, bI.hospitalName, bI.pickUpDrop, 
                    bI.documentURI, cM.message, bM.distance, bM.isAccepted
                    FROM bloodInfo as bI
                    RIGHT JOIN bloodMapping as bM on bM.receiver = bI.mobileNumber
                    LEFT JOIN customMessage cM on bI.mobileNumber = cM.mobileNumber
                    WHERE bM.donor = '{}' and bI.isActive = 1 and cM.contentType = 0
        '''.format(mobileNumber)

        values = conn.execute(query)
        responses = []
        for value in values:
            value = dict(value)
            value['bloodType'] = bloodMap[value['bloodType']]
            responses.append(value)

        return responses


@app.get('/blood/receive/{mobileNumber}',
         tags=["blood"])
async def blood_donate_data(mobileNumber: str):
    with engine.connect() as conn:
        query0 = ''' SELECT donor, receiver, distance, isAccepted
        FROM bloodMapping as bM
        WHERE bM.receiver = '{}'
        '''.format(mobileNumber)

        values = conn.execute(query0)
        responses = []
        for value in values:
            responses.append(value)

        return responses


# Needs to be tested briefly
@app.post('/blood/accept/{donor}/{receiver}',
          tags=["blood"])
def blood_accept(donor: str, receiver: str):
    with engine.connect() as conn:
        query0 = ''' UPDATE bloodMapping SET isAccepted = 1 where donor = '{0}' and receiver = '{1}'
        '''.format(donor, receiver)

        conn.execute(query0)

        query1 = '''UPDATE bloodInfo SET isActive = 0, updatedAt = now() 
        WHERE mobileNumber = '{0}' or mobileNumber = '{1}'
        '''.format(donor, receiver)

        conn.execute(query1)

        query2 = '''DELETE FROM bloodMapping where (donor = '{0}' or receiver = '{0}') and isAccepted = 0
        '''.format(donor, receiver)

        conn.execute(query2)

        return {
            "message": "Request Processed Successfully"
        }


@app.post('/oxygen/receive/',
          tags=["oxygen"])
async def oxygen_receive_request(oxygenreceive: OxygenReceive):
    with engine.connect() as conn:
        query = ''' SELECT mobileNumber, ( 6371 * acos( cos( radians({0}) ) * cos( radians( latitude ) )
                * cos( radians( longitude ) - radians({1}) ) + sin( radians({2}) ) * sin(radians(latitude)) ) ) 
                AS distance
                FROM oxygenInfo 
                WHERE oxygenReceiver = 0 AND isActive = 1
                HAVING distance < 500
                ORDER BY distance
                LIMIT 0 , 3;'''.format(oxygenreceive.latitude, oxygenreceive.longitude, oxygenreceive.latitude)

        values = conn.execute(query)
        k = 0
        for value in values:
            query2 = ''' INSERT INTO oxygenMapping(receiver, donor, distance) VALUES ('{}','{}',{})
            '''.format(oxygenreceive.mobileNumber, value[0], value[1])
            conn.execute(query2)
            k += 1

        query3 = '''INSERT INTO customMessage(mobileNumber, message, contentType) 
        VALUES('{0}','{1}',1)
        '''.format(oxygenreceive.mobileNumber, oxygenreceive.oxygenMessage)
        conn.execute(query3)

        return {
            "userNotified": k
        }


@app.post('/user/forgotPassword',
          tags=["user"])
def forgot_password(reset_password: resetPassword):
    hashed_password = get_password_hash(reset_password.password)
    with engine.connect() as conn:
        query0 = '''SELECT * FROM users WHERE mobileNumber = '{}' '''.format(reset_password.mobileNumber)
        result = conn.execute(query0)
        k = 0
        for r in result:
            k+=1

        if k == 0:
            return {
                'message': "User Doesn't Exist"
            }
        else:
            query = '''UPDATE users SET password = '{}', updatedAt = now() WHERE mobileNumber = '{}'
                                '''.format(hashed_password, reset_password.mobileNumber)

            result = conn.execute(query)
            return {
                'message': 'Password Changed Successfully'
            }




