from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fast_api.app.database import Database
from fast_api.app.models import (
    PerevalAdded, PerevalResponse, StatusEnum,
    PerevalListResponse, UserBase
)
from typing import List
from datetime import datetime
import logging
from database import Database


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API для ФСТР",
    description="API для работы с перевалами Федерация Спортивного Туризма России",
    version="1.0.0",
    contact={
        "name": "Поддержка",
        "email": "support@fstr.ru",
    },
    license_info={
        "name": "MIT",
    },
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="FSTR API",
        version="1.0.0",
        description="API для Федерация Спортивного Туризма России",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.post("/submitData/", response_model=PerevalResponse)
async def submit_data(pereval: PerevalAdded):
    try:
        with Database.get_cursor() as cursor:
            # Проверка существования пользователя
            cursor.execute(
                "SELECT id FROM users WHERE email = %s",
                (pereval.user.email,)
            )
            user_data = cursor.fetchone()

            if not user_data:
                cursor.execute(
                    """INSERT INTO users (email, fam, name, otc, phone)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id""",
                    (
                        pereval.user.email,
                        pereval.user.fam,
                        pereval.user.name,
                        pereval.user.otc,
                        pereval.user.phone,
                    )
                )
                user_id = cursor.fetchone()[0]
            else:
                user_id = user_data[0]


            cursor.execute(
                """INSERT INTO coords (latitude, longitude, height)
                VALUES (%s, %s, %s)
                RETURNING id""",
                (
                    pereval.coords.latitude,
                    pereval.coords.longitude,
                    pereval.coords.height,
                )
            )
            coords_id = cursor.fetchone()[0]


            cursor.execute(
                """INSERT INTO pereval_added (
                    user_id, coords_id, beauty_title, title,
                    other_titles, connect, add_time, status,
                    winter_level, summer_level, autumn_level, spring_level
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id""",
                (
                    user_id,
                    coords_id,
                    pereval.beauty_title,
                    pereval.title,
                    pereval.other_titles,
                    pereval.connect,
                    datetime.now(),
                    StatusEnum.new.value,
                    pereval.level.winter,
                    pereval.level.summer,
                    pereval.level.autumn,
                    pereval.level.spring,
                )
            )
            pereval_id = cursor.fetchone()[0]


            for image in pereval.images:
                cursor.execute(
                    """INSERT INTO pereval_images (pereval_id, image, title)
                    VALUES (%s, %s, %s)""",
                    (pereval_id, image.data, image.title)
                )

            return PerevalResponse(
                status=1,
                message="Запрос успешно обработан",
                id=pereval_id,
            )

    except Exception as e:
        logger.error(f"Error in submit_data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.get("/submitData/{pereval_id}", response_model=PerevalAdded)
async def get_pereval(pereval_id: int):
    try:
        with Database.get_cursor() as cursor:

            cursor.execute(
                """SELECT p.*, u.email, u.fam, u.name, u.otc, u.phone,
                   c.latitude, c.longitude, c.height
                FROM pereval_added p
                JOIN users u ON p.user_id = u.id
                JOIN coords c ON p.coords_id = c.id
                WHERE p.id = %s""",
                (pereval_id,)
            )
            pereval_data = cursor.fetchone()

            if not pereval_data:
                raise HTTPException(status_code=404, detail="Pereval not found")


            cursor.execute(
                "SELECT image, title FROM pereval_images WHERE pereval_id = %s",
                (pereval_id,)
            )
            images_data = cursor.fetchall()

            return {
                "user": {
                    "email": pereval_data[7],
                    "fam": pereval_data[8],
                    "name": pereval_data[9],
                    "otc": pereval_data[10],
                    "phone": pereval_data[11]
                },
                "coords": {
                    "latitude": pereval_data[12],
                    "longitude": pereval_data[13],
                    "height": pereval_data[14]
                },
                "level": {
                    "winter": pereval_data[15],
                    "summer": pereval_data[16],
                    "autumn": pereval_data[17],
                    "spring": pereval_data[18]
                },
                "images": [{"data": img[0], "title": img[1]} for img in images_data],
                "beautyTitle": pereval_data[3],
                "title": pereval_data[4],
                "other_titles": pereval_data[5],
                "connect": pereval_data[6],
                "status": pereval_data[2]
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_pereval: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.patch("/submitData/{pereval_id}", response_model=PerevalResponse)
async def update_pereval(pereval_id: int, pereval: PerevalAdded):
    try:
        with Database.get_cursor() as cursor:

            cursor.execute(
                "SELECT status FROM pereval_added WHERE id = %s",
                (pereval_id,)
            )
            status = cursor.fetchone()

            if not status:
                raise HTTPException(status_code=404, detail="Pereval not found")

            if status[0] != StatusEnum.new.value:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": 0,
                        "message": "Pereval cannot be edited as its status is not 'new'"
                    }
                )


            cursor.execute(
                """UPDATE coords SET latitude = %s, longitude = %s, height = %s
                WHERE id = (SELECT coords_id FROM pereval_added WHERE id = %s)""",
                (
                    pereval.coords.latitude,
                    pereval.coords.longitude,
                    pereval.coords.height,
                    pereval_id
                )
            )


            cursor.execute(
                """UPDATE pereval_added
                SET beauty_title = %s, title = %s, other_titles = %s, connect = %s,
                    winter_level = %s, summer_level = %s, autumn_level = %s, spring_level = %s
                WHERE id = %s""",
                (
                    pereval.beauty_title,
                    pereval.title,
                    pereval.other_titles,
                    pereval.connect,
                    pereval.level.winter,
                    pereval.level.summer,
                    pereval.level.autumn,
                    pereval.level.spring,
                    pereval_id
                )
            )


            cursor.execute(
                "DELETE FROM pereval_images WHERE pereval_id = %s",
                (pereval_id,)
            )


            for image in pereval.images:
                cursor.execute(
                    """INSERT INTO pereval_images (pereval_id, image, title)
                    VALUES (%s, %s, %s)""",
                    (pereval_id, image.data, image.title)
                )

            return PerevalResponse(
                status=1,
                message="Запрос успешно обработан",
                id=pereval_id,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_pereval: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/submitData/", response_model=List[PerevalListResponse])
async def get_user_perevals(user_email: str = Query(..., alias="user__email")):
    try:
        with Database.get_cursor() as cursor:
            cursor.execute(
                """SELECT p.id, p.status, p.title, p.beauty_title, p.add_time
                FROM pereval_added p
                JOIN users u ON p.user_id = u.id
                WHERE u.email = %s
                ORDER BY p.add_time DESC""",
                (user_email,)
            )
            perevals = cursor.fetchall()

            return [
                {
                    "id": p[0],
                    "status": p[1],
                    "title": p[2],
                    "beauty_title": p[3],
                    "date_added": p[4]
                }
                for p in perevals
            ]

    except Exception as e:
        logger.error(f"Error in get_user_perevals: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)