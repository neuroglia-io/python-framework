from rx.subject import Subject


class CloudEventBus:
    ''' Defines the fundamentals of a service used to manage incoming and outgoing streams of cloud events '''

    input_stream: Subject = Subject()
    ''' Gets the stream of events ingested by the application '''

    output_stream: Subject = Subject()
    ''' Gets the stream of events published by the application '''
