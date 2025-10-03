

cdef class Server:

    def __init__(self, name : str, weight : int  = 1):
        self.name = name
        self.weight = weight
        self.current_weight = 0
        self.effective_weight = weight
        self.active_connections = 0
        self.healthy = True


    cpdef str get_name(self):
        return self.name

    cpdef int get_weight(self):
        return self.weight

    cpdef void increment_connections(self):
        self.active_connections += 1

    cpdef void decrement_connections(self):
        if self.active_connections > 0:
            self.active_connections -= 1

    cpdef bint is_healthy(self):
        return self.healthy

    cpdef void set_healthy(self, bint status):
        self.healthy = status
