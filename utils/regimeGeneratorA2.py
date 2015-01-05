#!/usr/bin/python2
# -*- coding: utf-8 -*-

import numpy as np
import os

controllerList = ['FController', 'GController', 'JController',\
                'LSSController', 'PIFeedbackController']
               
#TODO: überlege, in welchem Punkt Regler linearisiert werden und dazu Pole
number = 4
pol = -1.5
#poles = [pol, pol, pol, pol]
fRange = [0.1, 0.6]
fStepSize = 0.05
ampl = 0.5

lines = ''
controller = controllerList[number]

if controller == 'PIFeedbackController':
    poles = [pol, pol, pol, pol, pol]
else:
    poles = [pol, pol, pol, pol]

# load head file
filePath = os.path.join('A2_head.sray')
with open(filePath, 'r') as f:
    head = f.read()

fs = np.arange(fRange[0],fRange[1] + fStepSize, fStepSize)
lines += '\n'

for f in fs:
        lines += '- name: A2_' + controller + '_f' + str(f) + '\n'
        lines += '  clear previous: !!python/bool False' + '\n'
        lines += '\n'
        lines += '  controller: ' + '\n'
        lines += '   type: '  + controller + '\n'
        lines += '   poles: ' + str(poles) + '\n'
        lines += '\n'
        lines += '  trajectory:' +'\n'
        lines += '   type: HarmonicTrajectory' + '\n'
        lines += '   Amplitude: ' + str(ampl) + '\n'
        lines += '   Frequency: ' + str(f) + '\n'
        lines += '\n'
               
#write results
#print os.path.pardir
dirPath = os.path.join(os.path.pardir, os.path.pardir, 'regimes', 'generated')
if not os.path.isdir(dirPath):
    os.makedirs(dirPath)

fileName = 'A2_' + controller + '_fRange(' + str(fRange[0])\
            + ',' + str(fRange[1]) + ')'+'A'+str(ampl)+'.sreg'
            
filePath = os.path.join(dirPath, fileName)   

with open(filePath, 'w') as f:
    f.write(head)    
    f.write(lines)
    
    
    
    
