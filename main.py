import os
from pydantic import BaseModel
from fastapi import FastAPI, Query
from sqlalchemy import create_engine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

host = os.environ['HOST']
user = os.environ['USER']
password = os.environ['PASSWORD']
database = os.environ['DATABASE']
port = os.environ['PORT']

engine = create_engine('mysql+pymysql://{}:{}@{}/{}'.format(user,password,host,database))

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
    oxygenReciever: bool = Query(...)
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


app = FastAPI(
    title="COVAID Backend",
    description="Backend for COVAID",
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



@app.post('/blood/entry')
async def blood_entry(blood: Blood):
    with engine.connect() as conn:
        recoveryDate = blood.recoveryDate.split('T')[0] + " 00:00:00"
        query = '''INSERT INTO bloodInfo(mobileNumber, bloodReceiver, bloodType, hospitalName, pickUpDrop, documentURI, 
        recoveryDate, distanceWillingToTravel, detailsAvailable, latitude, longitude, createdAt, updatedAt) 
        values ('{0}',{1},{2},'{3}',{4},'{5}','{6}',{7},{8},{9},{10}, now(), now())'''.format(blood.mobileNumber,
                                                                                              blood.bloodReceiver,
                                                                                   blood.bloodType, blood.hospitalName,
                                                                                   blood.pickUpDrop, blood.documentURI,
                                                                                   recoveryDate, blood.distanceWillingToTravel,
                                                                                   blood.detailsAvailable, blood.latitude,
                                                                                   blood.longitude)

        status = conn.execute(query)
        return "Hello"


@app.post('/oxygen/entry')
async def oxygen_entry(oxygen:Oxygen):
    with engine.connect() as conn:
        query = '''INSERT INTO oxygenInfo(mobileNumber, oxygenReceiver, hospitalName, fullGear, canDeliver, 
                detailsAvailable, latitude, longitude, createdAt, updatedAt) 
                values ('{0}',{1},'{2}',{3},{4},{5},{6},{7},now(), now())'''.format(oxygen.mobileNumber, oxygen.oxygenReciever,
                                                                                    oxygen.hospitalName, oxygen.fullGear,
                                                                                    oxygen.canDeliver, oxygen.oxygenDetailsAvailable,
                                                                                    oxygen.latitude, oxygen.longitude)

        status = conn.execute(query)
        return "Hello"

@app.get('/blood/{mobileNumber}')
async def blood_get(mobileNumber: str):
    with engine.connect() as conn:
        query = '''SELECT * FROM bloodInfo WHERE mobileNumber = '{}' '''.format(mobileNumber)
        values = conn.execute(query)

        for value in values:
            return value

        return {
            'status': 400
        }

@app.get('/oxygen/{mobileNumber}')
async def blood_get(mobileNumber: str):
    with engine.connect() as conn:
        query = '''SELECT * FROM oxygenInfo WHERE mobileNumber = '{}' '''.format(mobileNumber)
        values = conn.execute(query)

        for value in values:
            return value

        return {
            'status': 400
        }

@app.post('/blood/receive/')
async def blood_receive_request(bloodreceive: BloodReceive):
    with engine.connect() as conn:
        query =''' SELECT mobileNumber, ( 6371 * acos( cos( radians({0}) ) * cos( radians( latitude ) )
                * cos( radians( longitude ) - radians({1}) ) + sin( radians({2}) ) * sin(radians(latitude)) ) ) AS distance
                FROM bloodInfo 
                WHERE bloodReceiver = 0 AND isActive = 1
                HAVING distance < 500
                ORDER BY distance
                LIMIT 0 , 3;'''.format(bloodreceive.latitude, bloodreceive.longitude, bloodreceive.latitude)

        values = conn.execute(query)
        k = 0
        for value in values:
            query2 = ''' INSERT INTO bloodMapping(receiver, donor, distance) VALUES ('{}','{}',{})
            '''.format(bloodreceive.mobileNumber, value[0], value[1])
            res2 = conn.execute(query2)
            k+=1

        query3 = '''INSERT INTO customMessage(mobileNumber, message, contentType) 
        VALUES('{0}','{1}',0)
        '''.format(bloodreceive.mobileNumber, bloodreceive.bloodMessage)
        res3 = conn.execute(query3)

        return {
            "userNotified": k
        }

@app.get('/blood/donate/{mobileNumber}')
async def blood_donate_data(mobileNumber: str):
    with engine.connect() as conn:
        query0 = ''' SELECT bI.bloodType, bI.hospitalName, bI.pickUpDrop, bI.documentURI, bM.donor, bM.receiver 
        FROM bloodInfo as bI, bloodMapping as bM 
        WHERE bM.donor = '{}' AND bM.isAccepted = 1 and bI.mobileNumber = bM.receiver
        '''.format(mobileNumber)
        values = conn.execute(query0)
        for value in values:
            return  [value]

        query = '''SELECT bI.bloodType, bI.hospitalName, bI.pickUpDrop, bI.documentURI, cM.message, bM.distance
                    FROM bloodInfo as bI
                    RIGHT JOIN bloodMapping as bM on bM.receiver = bI.mobileNumber
                    LEFT JOIN customMessage cM on bI.mobileNumber = cM.mobileNumber
                    WHERE bM.donor = '{}' and bI.isActive = 1 and cM.contentType = 0
        '''.format(mobileNumber)

        values = conn.execute(query)
        respones = []
        for value in values:
            respones.append(value)

        return respones


#Needs to be tested briefly
@app.post('/blood/accept/{donor}/{receiver}')
def blood_accept(donor: str, receiver: str):
    with engine.connect() as conn:
        query0 = ''' UPDATE bloodMapping SET isAccepted = 1 where donor = '{0}' and receiver = '{1}'
        '''.format(donor, receiver)

        conn.execute(query0)

        query1 = '''UPDATE bloodInfo SET isActive = 0 where mobileNumber = '{0}' or mobileNumber = '{1}'
        '''.format(donor, receiver)

        conn.execute(query1)

        query2 = '''DELETE FROM bloodMapping where (donor = '{0}' or receiver = '{0}') and isAccepted = 0
        '''.format(donor, receiver)

        conn.execute(query2)

        return {
            "message": "Request Processed Successfully"
        }

@app.post('/oxygen/receive/')
async def oxygen_receive_request(oxygenreceive: OxygenReceive):
    with engine.connect() as conn:
        query =''' SELECT mobileNumber, ( 6371 * acos( cos( radians({0}) ) * cos( radians( latitude ) )
                * cos( radians( longitude ) - radians({1}) ) + sin( radians({2}) ) * sin(radians(latitude)) ) ) AS distance
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
            res2 = conn.execute(query2)
            k+=1

        query3 = '''INSERT INTO customMessage(mobileNumber, message, contentType) 
        VALUES('{0}','{1}',1)
        '''.format(oxygenreceive.mobileNumber, oxygenreceive.oxygenMessage)
        res3 = conn.execute(query3)

        return {
            "userNotified": k
        }
