#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar  9 17:58:54 2023

@author: prpa
"""

"""
Solution to the one-way tunnel
En esta opcion se cede el turno de forma general en forma circular de prioridad, 
siempre que tengan alguno esperando, si no, no hay necesidad cambiar semaforo.
Ademas solo pueden entrar si es su turno o si no hay ninguno de las otras clases esperando
"""
import time
import random
from multiprocessing import Lock, Condition, Process
from multiprocessing import Value

SOUTH = 1
NORTH = 0

NCARS = 100
NPED = 10
TIME_CARS = 0.5  # a new car enters each 0.5s
TIME_PED = 5 # a new pedestrian enters each 5s
TIME_IN_BRIDGE_CARS = (1, 0.5) # normal 1s, 0.5s
TIME_IN_BRIDGE_PEDESTRGIAN = (30, 10) # normal 1s, 0.5s

class Monitor():
    def __init__(self):
        self.mutex = Lock()
        self.patata=Value('i',0)  #Ayuda a prevenir posibles problemas de sincronizacion de los procesos
        #cuenta las veces que se adquiere el mutex , ayuda a evitar condiciones de carrera
        self.Ncoches= Value('i',0)  #Numero coches Norte
        self.Scoches = Value('i',0) #Numero coches Sur
        self.Nwaiting = Value('i',0) #Coches esperando Norte
        self.Swaiting = Value('i',0) #Coches esperando Sur
        self.np = Value('i',0)   #Numero peatones
        self.Pwaiting = Value('i',0) #Numero peatones esperando
        self.turn = Value('i', 0) #0-Peatones 1-Norte 2-Sur
        self.puede_pasar_south = Condition(self.mutex)
        self.puede_pasar_north = Condition(self.mutex)
        self.puede_pasar_peaton = Condition(self.mutex)
       
    def pasan_south(self):
        return self.Ncoches.value==0 and self.np.value==0 and \
            (self.turn.value==2 or (self.Pwaiting.value==0 and self.Nwaiting.value==0))
    
    def pasan_north(self):
        return self.Scoches.value==0 and self.np.value==0 and \
            (self.turn.value==1 or (self.Pwaiting.value==0 and self.Swaiting.value==0))

    def wants_enter_car(self, direction: int) -> None:
        self.mutex.acquire()
        self.patata.value+=1
        if(direction==SOUTH):
            self.Swaiting.value +=1
            self.puede_pasar_south.wait_for(self.pasan_south)
            self.Swaiting.value -=1
            self.Scoches.value+=1
        if(direction==NORTH):
            self.Nwaiting.value+=1            
            self.puede_pasar_north.wait_for(self.pasan_north)
            self.Nwaiting.value-=1
            self.Ncoches.value+=1
        self.mutex.release()
    
    def pasan_peatones(self):
        return self.Ncoches.value==0 and self.Scoches.value==0 and \
            (self.turn.value==0 or (self.Nwaiting.value==0 and self.Swaiting.value==0))

    def leaves_car(self, direction: int) -> None:
        self.mutex.acquire() 
        self.patata.value+=1
        if(direction==SOUTH):
            self.Scoches.value-=1
            if (self.Nwaiting.value>0):
                self.turn.value = 1
            elif(self.Pwaiting.value>0):
                self.turn.value=0
            self.puede_pasar_north.notify_all()
            self.puede_pasar_peaton.notify_all()  
        if(direction==NORTH):
            self.Ncoches.value-=1
            if(self.Pwaiting.value>0):
                self.turn.value=0
            elif(self.Swaiting.value>0):
                self.turn.value=2
            self.puede_pasar_peaton.notify_all() 
            self.puede_pasar_south.notify_all()
        self.mutex.release()

    def wants_enter_pedestrian(self) -> None:
        self.mutex.acquire()
        self.patata.value+=1
        self.Pwaiting.value += 1
        self.puede_pasar_peaton.wait_for(self.pasan_peatones)
        self.Pwaiting.value -= 1
        self.np.value += 1
        self.mutex.release()

    def leaves_pedestrian(self) -> None:
        self.mutex.acquire()
        self.patata.value+=1
        self.np.value-=1 
        if(self.Swaiting.value>0):
            self.turn.value = 2
        elif(self.Nwaiting.value>0):
            self.turn.value=1
        self.puede_pasar_south.notify_all()
        self.puede_pasar_north.notify_all()
        self.mutex.release()

    def __repr__(self) -> str:
        return f'Monitor: {self.patata.value}'

def delay(d=3):
    time.sleep(random.random()/d)

def delay_car_north() -> None: #El tiempo de espera sigue una normal, evitando que sean valores negativos
    x=random.gauss(1,0.5)
    if x<0:
        time.sleep(0.01)
    else:
        time.sleep(x)

def delay_car_south() -> None:
    x=random.gauss(1,0.5)
    if x<0:
        time.sleep(0.01)
    else:
        time.sleep(x)

def delay_pedestrian() -> None:
    x=random.gauss(5,1)
    if x<0:
        time.sleep(0.01)
    else:
        time.sleep(x)

def car(cid: int, direction: int, monitor: Monitor)  -> None:
    print(f"car {cid} heading {direction} wants to enter. {monitor}")
    monitor.wants_enter_car(direction)
    print(f"car {cid} heading {direction} enters the bridge. {monitor}")
    if direction==NORTH :
        delay_car_north()
    else:
        delay_car_south()
    print(f"car {cid} heading {direction} leaving the bridge. {monitor}")
    monitor.leaves_car(direction)
    print(f"car {cid} heading {direction} out of the bridge. {monitor}")

def pedestrian(pid: int, monitor: Monitor) -> None:
    print(f"pedestrian {pid} wants to enter. {monitor}")
    monitor.wants_enter_pedestrian()
    print(f"pedestrian {pid} enters the bridge. {monitor}")
    delay_pedestrian()
    print(f"pedestrian {pid} leaving the bridge. {monitor}")
    monitor.leaves_pedestrian()
    print(f"pedestrian {pid} out of the bridge. {monitor}")



def gen_pedestrian(monitor: Monitor) -> None:
    pid = 0
    plst = []
    for _ in range(NPED):
        pid += 1
        p = Process(target=pedestrian, args=(pid, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/TIME_PED))

    for p in plst:
        p.join()

def gen_cars(monitor) -> Monitor:
    cid = 0
    plst = []
    for _ in range(NCARS):
        direction = NORTH if random.randint(0,1)==1  else SOUTH
        cid += 1
        p = Process(target=car, args=(cid, direction, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/TIME_CARS))

    for p in plst:
        p.join()

def main():
    monitor = Monitor()
    gcars = Process(target=gen_cars, args=(monitor,))
    gped = Process(target=gen_pedestrian, args=(monitor,))
    gcars.start()
    gped.start()
    gcars.join()
    gped.join()


if __name__ == '__main__':
    main()
