import os
from pydantic import BaseModel
from fastapi import FastAPI, Query
from sqlalchemy import create_engine

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
    mobileNumber: int = Query(...)
    oxygenReciever: bool = Query(...)
    hospitalName: str = Query(...)
    fullGear: bool = Query(...)
    canDeliver: bool = Query(...)
    oxygenDetailsAvailable: bool = Query(...)
    latitude: float
    longitude: float

app = FastAPI(
    title="COVAID Backend",
    description="Backend for COVAID",
    version="0.1.0",
    openapi_url="/api/v0.1.0/openapi.json",
    docs_url="/",
    redoc_url=None
)


@app.post('/blood/entry')
async def blood_entry(blood: Blood):
    with engine.connect() as conn:
        recoveryDate = blood.recoveryDate.split('T')[0] + " 00:00:00"
        query = '''INSERT INTO bloodinfo(mobileNumber, bloodReceiver, bloodType, hospitalName, pickUpDrop, documentURI, 
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
        query = '''INSERT INTO oxygeninfo(mobileNumber, oxygenReceiver, hospitalName, fullGear, canDeliver, 
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
        query = '''SELECT * FROM bloodinfo WHERE mobileNumber = '{}' '''.format(mobileNumber)
        values = conn.execute(query)

        for value in values:
            return value

        return {
            'status': 400
        }

@app.get('/oxygen/{mobileNumber}')
async def blood_get(mobileNumber: str):
    with engine.connect() as conn:
        query = '''SELECT * FROM oxygeninfo WHERE mobileNumber = '{}' '''.format(mobileNumber)
        values = conn.execute(query)

        for value in values:
            return value

        return {
            'status': 400
        }


