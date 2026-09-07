from fastapi import APIRouter, HTTPException, status

from app.domain.entities import Bike
from .dependencies import BikeServiceDependency
from .schemas import (
    BikeCreateWebRequest,
    BikeUpdateWebRequest,
    BikeWebResponse,
    BikeListWebResponse,
)

bike_router = APIRouter(
    prefix="/bikes",
    tags=["bikes"],
)


@bike_router.get("/", response_model=BikeListWebResponse)
async def list_bikes(bike_service: BikeServiceDependency):
    bikes = await bike_service.list_bikes()
    bike_responses = [
        BikeWebResponse(
            id=bike.id or 0,
            brand=bike.brand,
            model=bike.model,
            bike_type=bike.bike_type,
        )
        for bike in bikes
        if bike.id is not None
    ]
    return BikeListWebResponse(
        data=bike_responses,
    )


@bike_router.get("/{bike_id}", response_model=BikeWebResponse)
async def get_bike(bike_id: int, bike_service: BikeServiceDependency):
    bike = await bike_service.get_bike(bike_id)
    if not bike or bike.id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "errors": [
                    {
                        "code": "BIKE_NOT_FOUND",
                        "message": "Bike not found",
                        "details": f"No bike found with id: {bike_id}",
                    }
                ]
            },
        )
    return BikeWebResponse(
        id=bike.id, brand=bike.brand, model=bike.model, bike_type=bike.bike_type
    )


@bike_router.post(
    "/", response_model=BikeWebResponse, status_code=status.HTTP_201_CREATED
)
async def create_bike(
    bike_data: BikeCreateWebRequest, bike_service: BikeServiceDependency
):
    """Create a new bike."""
    bike = Bike(
        brand=bike_data.brand, model=bike_data.model, bike_type=bike_data.bike_type
    )
    created_bike = await bike_service.create_bike(bike)
    if created_bike.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "errors": [
                    {
                        "code": "CREATION_FAILED",
                        "message": "Failed to create bike",
                        "details": "Bike was not assigned an ID after creation",
                    }
                ]
            },
        )
    return BikeWebResponse(
        id=created_bike.id,
        brand=created_bike.brand,
        model=created_bike.model,
        bike_type=created_bike.bike_type,
    )


@bike_router.put("/{bike_id}", response_model=BikeWebResponse)
async def update_bike(
    bike_id: int, bike_data: BikeUpdateWebRequest, bike_service: BikeServiceDependency
):
    """Update an existing bike."""
    updated_bike = await bike_service.update_bike(
        bike_id,
        Bike(
            brand=bike_data.brand, model=bike_data.model, bike_type=bike_data.bike_type
        ),
    )
    if not updated_bike or updated_bike.id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "errors": [
                    {
                        "code": "BIKE_NOT_FOUND",
                        "message": "Bike not found",
                        "details": f"No bike found with id: {bike_id}",
                    }
                ]
            },
        )
    return BikeWebResponse(
        id=updated_bike.id,
        brand=updated_bike.brand,
        model=updated_bike.model,
        bike_type=updated_bike.bike_type,
    )


@bike_router.delete("/{bike_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bike(bike_id: int, bike_service: BikeServiceDependency):
    """Delete a bike."""
    deleted = await bike_service.delete_bike(bike_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "errors": [
                    {
                        "code": "BIKE_NOT_FOUND",
                        "message": "Bike not found",
                        "details": f"No bike found with id: {bike_id}",
                    }
                ]
            },
        )
