from random import Random

cdef class LoadBalancer:
    cdef list servers
    cdef int current_index
    cdef int total_weight
    cdef list cumulative_weights
    cdef object random
    cdef int strategy



    def __init__(self, servers, strategy = 1):
        self.servers = servers
        self.current_index = 0
        self.total_weight = self._calculate_total_weight()
        self.strategy = strategy
        self.random = Random()
        self.cumulative_weights = self._calculate_cumulative_weights()


    cpdef int _calculate_total_weight(self):
        cdef int total = 0
        cdef object s
        for s in self.servers:
            if s.healthy:
                total += s.weight
        return total

    cpdef list _calculate_cumulative_weights(self):
        cdef list weight = []
        cdef int cumulative = 0
        cdef object s
        for s in self.servers:
            if s.healthy:
                cumulative += s.weight
                weight.append(cumulative)
        return weight


    cpdef list _get_healthy_server(self):
        cdef list healthy = []
        cdef object s
        for s in self.servers:
            if s.healthy:
                healthy.append(s)
        return healthy


    cdef object _round_robin(self):
        cdef list healthy = self._get_healthy_server()
        if not healthy:
            return None

        cdef object s = healthy[self.current_index % len(healthy)]
        self.current_index += 1
        return s


    cdef object _weighted_round_robin(self):
        cdef object best = None
        cdef int total = 0
        cdef object s

        for s in self.servers:
            if not s.healthy:
                continue
            s.current_weight += s.effective_weight
            total += s.effective_weight

            if best is None or s.current_weight > best.current_weight:
                best = s

        if best is not None:
            best.current_weight -= total
        return best


    cpdef object _random(self):
        cdef list healthy = self._get_healthy_server()
        if not healthy:
            return None
        return healthy[self.random.randint(0, len(healthy) - 1)]

    cdef object _weighted_random(self):
        cdef list healthy = self._get_healthy_server()
        if not healthy:
            return None

        cdef int random_value = self.random.randint(0, self.total_weight - 1)
        cdef int i
        for i in range(len(self.cumulative_weights)):
            if random_value < self.cumulative_weights[i]:
                return healthy[i]

        return healthy[-1]

    cdef object _least_connections(self):
        cdef object best = None
        cdef object s

        for s in self.servers:
            if not s.healthy:
                continue
            if best is None or s.active_connections < best.active_connections:
                best = s

        return best

    cpdef void refresh_weight(self):
        self.total_weight = self._calculate_total_weight()
        self.cumulative_weights = self._calculate_cumulative_weights()

    cpdef object get_next_server(self):
        # 0: ROUND_ROBIN, 1: WEIGHTED_ROUND_ROBIN, 2: RANDOM, 3: WEIGHTED_RANDOM, 4: LEAST_CONNECTIONS
        if self.strategy == 0:
            return self._round_robin()
        elif self.strategy == 1:
            return self._weighted_round_robin()
        elif self.strategy == 2:
            return self._random()
        elif self.strategy == 3:
            return self._weighted_random()
        elif self.strategy == 4:
            return self._least_connections()
        return self.servers[0] if self.servers else None
