from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import validators
from prisma import Prisma
from dotenv import load_dotenv
import os
from recordprocess import record_video, process_video, upload_final_video,clean_up
from logger import ColoredLogger
import logging
load_dotenv()

API_KEY = os.getenv("API_KEY")


# Initialize Prisma Client
prisma = Prisma()

app = FastAPI()
# Configure logging
#logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    # Connect to Prisma Client
    await prisma.connect()
    logger.info("Prisma connected")

@app.on_event("shutdown")
async def shutdown_event():
    # Disconnect Prisma Client
    await prisma.disconnect()
    logger.info("Prisma disconnected")

class URLRequest(BaseModel):
    id: int

@app.post("/record-and-process-video/")
async def record_and_process(request: URLRequest):
    try:


        # Check if the case is in construction
        status_history = await prisma.status_histories.find_first(
            where={
                'caseId': request.id,
                'name': 'in_construction'
            },
        )

        if not status_history:
            logger.info(f"Case {request.id} is not in construction")
          #  raise HTTPException(status_code=404, detail="Case not found or not in construction")

        logger.info(f"Case {request.id} is in construction")


        # Get the latest labo_link for the case_id
        latest_labo_link = await prisma.labo_links.find_first(
            where={
                'case_id': request.id
            },
            order={
                'id': 'desc'
            }
        )

        if not latest_labo_link:
            raise HTTPException(status_code=404, detail="No labo link found for the case")

        url = latest_labo_link.iiwgl_link

        # Validate the URL
        if not validators.url(url):
            logger.error(f"Invalid URL: {url}")
            raise HTTPException(status_code=400, detail="Invalid URL found for the case")

        logger.info(f"Obtained and validated URL: {url}")

        # Get case data
        case = await prisma.cases.find_unique(
            where={
                'id': request.id
            }
        )

        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        patient_id = case.patient_id
        doctor_id = case.doctor_id
        pack_id = case.pack_id

        # Get patient data
        patient = await prisma.patients.find_unique(
            where={
                'id': patient_id
            }
        )

        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        patient_name = f"{patient.first_name} {patient.last_name}"
        logger.info(f"Obtained patient name: {patient_name}")

        # Get doctor data
        doctor = await prisma.doctors.find_unique(
            where={
                'id': doctor_id
            }
        )

        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        user_id = doctor.user_id

        # Get user data (doctor's name)
        user = await prisma.users.find_unique(
            where={
                'id': user_id
            }
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        doctor_name = f"{user.first_name} {user.last_name}"
        logger.info(f"Obtained doctor name: {doctor_name}")

        # Get number of months duration
        nbr_months_duration = None
        if pack_id:
            pack = await prisma.packs.find_unique(
                where={
                    'id': pack_id
                }
            )
            if pack:
                nbr_months_duration = pack.nbr_months_duration
                logger.info(f"Obtained number of months duration: {nbr_months_duration}")

        # Record the video using the iiwgl_link
        record_video(url)

        # Process and upload the video
        process_video(patient_name, doctor_name, nbr_months_duration)
        upload_response = upload_final_video(API_KEY)
        logger.info(f"Obtained response url: {upload_response}")

        # Update the labo_links table with the API URL
        #updated_labo_link = await prisma.labo_links.update_many(
         #   where={
         #       'case_id': request.id
        #    },
         #   data={
         #       'video_id': upload_response['video_id']
         #   }
        #)

        #clean_up()
        return upload_response

    except HTTPException as http_err:
        raise http_err

    except Exception as e:
        logger.error(f"Database query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

# Run your FastAPI application with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
