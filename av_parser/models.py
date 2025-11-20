from typing import List, Dict, Optional

from pydantic import BaseModel


class BaggageInfo(BaseModel):
    count: int
    weight: Optional[int] = None


class Baggage(BaseModel):
    handbags: BaggageInfo
    baggage: BaggageInfo


class RuleInfo(BaseModel):
    available: bool
    is_from_config: bool


class Rules(BaseModel):
    return_before_flight: RuleInfo
    change_before_flight: RuleInfo


class FlightSegment(BaseModel):
    departure: str
    arrival: str
    departure_date: str
    arrival_date: str
    duration: int
    number: str
    marketing_carrier: str
    operating_carrier: str


class FlightInfo(BaseModel):
    forward: List[FlightSegment]


class FareInfo(BaseModel):
    fare_code: str
    trip_class: str
    baggage: Baggage
    rules: Rules


class Fare(BaseModel):
    fare_key: str
    fare_info: List[FareInfo]
    prices: dict[str, int]


class FlightOffer(BaseModel):
    is_vtrip: bool
    key: str
    flight_info: FlightInfo
    fares: List[Fare]
    prices: dict[str, int]
    duration: int
    min_price: int
    min_provider: str


class ServiceResponse(BaseModel):
    success: bool
    pid: str
    result: Dict[str, List[FlightOffer]]


## это для примера выгрузка первого FlightOffer

if __name__ == "__main__":
    sample_data = {
        "success": True,
        "pid": "some_pid",
        # process_id для того что бы отделять флоу процессов друг от друга (в логах процесса должен быть)
        "result": {
            "MOWLED20251217": [
                {
                    "is_vtrip": False,
                    # если len(FlightSegment) > 1 и marketing_carrier/operating_carrier в сегментах разные -> True
                    "key": "ZKD_ZLK_2025-12-17T15:30_236_772_R0_",
                    # уникальный ключ для нахождения одинаковых перелетов
                    "flight_info": {
                        "forward": [
                            {
                                "departure": "ZKD",
                                "arrival": "ZLK",
                                "departure_date": "2025-12-17T15:30",
                                "arrival_date": "2025-12-17T19:26",
                                "duration": 236,
                                "number": "772",
                                "marketing_carrier": "R0",
                                "operating_carrier": "R0"
                            }
                        ]
                    },
                    "fares": [
                        {
                            "fare_key": "1_0_0_0_1_36_0_0_0_1_0_0_0_0",  # уникальный ключ этого тарифа
                            "fare_info": [
                                {
                                    "fare_code": "Y_1PC36",
                                    "trip_class": "Y",
                                    "baggage": {
                                        "handbags": {
                                            "count": 1
                                        },
                                        "baggage": {
                                            "count": 1,
                                            "weight": 36
                                        }
                                    },
                                    "rules": {
                                        "return_before_flight": {
                                            "available": True,
                                            "is_from_config": True
                                        },
                                        "change_before_flight": {
                                            "available": False,
                                            "is_from_config": True
                                        }
                                    }
                                }
                            ],
                            "prices": {
                                "OneTwoTrip": 1592
                            }
                        }
                    ],
                    "prices": {
                        "OneTwoTrip": 1592
                    },
                    "duration": 236,
                    "min_price": 1592,
                    "min_provider": "OneTwoTrip"
                }
            ]
        }
    }

    print(ServiceResponse(**sample_data))
