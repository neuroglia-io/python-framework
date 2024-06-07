def cloudevent(cloud_event_type: str):
    def decorator(cls):
        cls.__cloudevent__type__ = cloud_event_type
        return cls
    return decorator
