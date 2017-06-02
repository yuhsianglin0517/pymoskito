# -*- coding: utf-8 -*-
import numpy as np
from scipy.linalg import solve_continuous_are
from collections import OrderedDict
import mpctools as mpc

import pymoskito as pm

from . import settings as st
from . import symbolic_calculation as symcalc


class LinearStateFeedback(pm.Controller):

    public_settings = OrderedDict([('poles', [-9, -7, -4, -2, -3, -2]),
                                   ("long pendulum", "u"),
                                   ("short pendulum", "o"),
                                   ('tick divider', 1)])

    def __init__(self, settings):
        # add specific private settings
        settings.update(input_order=0)
        settings.update(ouput_dim=1)
        settings.update(input_type='system_state')

        pm.Controller.__init__(self, settings)

        eq_state = calc_equilibrium(settings)
        # pole placement
        parameter = [st.m0, st.m1, st.m2, st.l1, st.l2, st.g, st.d0, st.d1, st.d2]
        self.A = symcalc.A_func(list(eq_state), parameter)
        self.B = symcalc.B_func(list(eq_state), parameter)
        self.C = symcalc.C
        self.K = pm.place_siso(self.A, self.B, self._settings['poles'])
        self.V = pm.calc_prefilter(self.A, self.B, self.C, self.K)
        # eig = np.linalg.eig(self.A - np.dot(self.B, self.K))

        self._logger.info("Equilibrium: {}".format(eq_state.tolist()))
        self._logger.info("Poles: {}".format(self._settings["poles"]))
        self._logger.info("K: {}".format(self.K[0]))
        self._logger.info("V: {}".format(self.V[0]))

    def _control(self, time, trajectory_values=None, feedforward_values=None,
                 input_values=None, **kwargs):
        # input abbreviations
        x = input_values
        yd = trajectory_values
        eq = kwargs.get("eq", None)

        if eq is None:
            eq = calc_closest_eq_state(self._settings, input_values)
        x = x - np.atleast_2d(eq).T

        # this is a second version
        # x = calc_small_signal_state(self._settings, is_values)

        # u corresponds to a force [kg*m/s**2] = [N]
        u = - np.dot(self.K, x) + np.dot(self.V, yd[0, 0])

        return u


class LinearStateFeedbackParLin(pm.Controller):

    public_settings = OrderedDict([('poles', [-9, -7, -4, -2, -3, -2]),
                                   ("long pendulum", "u"),
                                   ("short pendulum", "o"),
                                   ('tick divider', 1)])

    def __init__(self, settings):
        # add specific private settings
        settings.update(input_order=0)
        settings.update(ouput_dim=1)
        settings.update(input_type='system_state')

        pm.Controller.__init__(self, settings)

        eq_state = calc_equilibrium(settings)
        # pole placement
        parameter = [st.m0, st.m1, st.m2, st.l1, st.l2, st.g, st.d0, st.d1, st.d2]
        self.A = symcalc.A_func_par_lin(list(eq_state), parameter)
        self.B = symcalc.B_func_par_lin(list(eq_state), parameter)
        self.C = symcalc.C_par_lin
        self.K = pm.place_siso(self.A, self.B, self._settings['poles'])
        self.V = pm.calc_prefilter(self.A, self.B, self.C, self.K)
        # eig = np.linalg.eig(self.A - np.dot(self.B, self.K))

        self._logger.info("Equilibrium: {}".format(eq_state.tolist()))
        self._logger.info("Poles: {}".format(self._settings["poles"].tolist()))
        self._logger.info("K: {}".format(self.K.tolist()[0]))
        self._logger.info("V: {}".format(self.V[0]))

    def _control(self, time, trajectory_values=None, feedforward_values=None,
                 input_values=None, **kwargs):
        """

        :param time:
        :param trajectory_values:
        :param feedforward_values:
        :param input_values:
        :param kwargs:
        :return:
        """
        # input abbreviations
        x = input_values
        yd = trajectory_values
        eq = kwargs.get("eq", None)

        if eq is None:
            eq = calc_closest_eq_state(self._settings, input_values)
        x = x - np.atleast_2d(eq).T

        # this is a second version
        # x = calc_small_signal_state(self._settings, is_values)

        # u corresponds to a acceleration [m/s**2]
        u = - np.dot(self.K, x) + np.dot(self.V, yd[0, 0])

        return u


class LinearQuadraticRegulator(pm.Controller):

    public_settings = OrderedDict([("Q", [1, 0.063, 0.025, 0.025, 0.025, 0.025]),
                                   ("R", [1.0 / 144.0]),
                                   ("long pendulum", "u"),
                                   ("short pendulum", "o"),
                                   ("d0", 0.0),
                                   ('tick divider', 1)])

    def __init__(self, settings):
        # add specific private settings
        settings.update(input_order=0)
        settings.update(ouput_dim=1)
        settings.update(input_type='system_state')

        pm.Controller.__init__(self, settings)

        eq_state = calc_equilibrium(settings)
        # pole placement
        parameter = [st.m0, st.m1, st.m2, st.l1, st.l2, st.g, self._settings["d0"], st.d1, st.d2]
        self.A = symcalc.A_func(list(eq_state), parameter)
        self.B = symcalc.B_func(list(eq_state), parameter)
        self.C = symcalc.C

        # create Q and R matrix
        self.Q = np.diag(self._settings["Q"])
        self.R = np.diag(self._settings["R"])

        # try to solve linear riccati equation
        self.P = solve_continuous_are(self.A, self.B, self.Q, self.R)
        self.K = np.dot(np.dot(np.linalg.inv(self.R), self.B.T), self.P)
        self.V = pm.calc_prefilter(self.A, self.B, self.C, self.K)

        eig = np.linalg.eig(self.A - np.dot(self.B, self.K))

        self._logger.info("equilibrium = " + str(eq_state))
        self._logger.info("Q = " + str(self._settings["Q"]))
        self._logger.info("R = " + str(self._settings["R"]))
        self._logger.info("P = " + str(self.P))
        self._logger.info("K = " + str(self.K))
        self._logger.info("eig = " + str(eig))
        self._logger.info("V = " + str(self.V[0][0]))

    def _control(self, time, trajectory_values=None, feedforward_values=None,
                 input_values=None, **kwargs):
        # input abbreviations
        x = input_values
        yd = trajectory_values
        eq = kwargs.get("eq", None)

        if eq is None:
            eq = calc_closest_eq_state(self._settings, x)
        x = x - np.atleast_2d(eq).T

        # u corresponds to a force [kg*m/s**2] = [N]
        u = - np.dot(self.K, x) + np.dot(self.V, yd[0, 0])

        return u


class LjapunovController(pm.Controller):

    public_settings = OrderedDict([
        ("k", 8),
        ("long pendulum", "u"),
        ("short pendulum", "o"),
        ("tick divider", 1)])

    def __init__(self, settings):
        settings.update(input_order=0)
        settings.update(output_order=1)
        settings.update(input_type="system_state")
        pm.Controller.__init__(self, settings)

        self.w = st.m1*st.l1/(st.m2*st.l2)

    def _control(self, time, trajectory_values=None, feedforward_values=None,
                 input_values=None, **kwargs):
        x1, x2, x3, x4, x5, x6 = input_values

        E0 = 0.5*st.m0*x2**2
        E1 = 0
        E2 = 0

        if self._settings["long pendulum"] == "u":
            E1 = 0.5*st.m1*st.l1**2*x4**2 + st.m1*st.g*st.l1*(np.cos(x3) + 1)
        elif self._settings["long pendulum"] == "o":
            E1 = 0.5*st.m1*st.l1**2*x4**2 + st.m1*st.g*st.l1*(np.cos(x3) - 1)

        if self._settings["short pendulum"] == "u":
            E2 = 0.5*st.m2*st.l2**2*x6**2 + st.m2*st.g*st.l2*(np.cos(x5) + 1)
        elif self._settings["short pendulum"] == "o":
            E2 = 0.5*st.m2*st.l2**2*x6**2 + st.m2*st.g*st.l2*(np.cos(x5) - 1)

        G = st.m0*x2*E0 + st.m1*st.l1*x4*np.cos(x3)*E1 + st.m2*st.l2*x6*np.cos(x5)*E2*self.w**2

        u_lja = -self._settings["k"]*G  # + (st.d1*E1*x4**2 + st.d2*E2*x6**2)/G

        # the u of the ljapunov method is a acceleration and the model require a force
        d0 = 0
        d1 = 0
        d2 = 0
        M1_star = 0
        M2_star = 0

        M = st.m0 + st.m1*(np.sin(x3))**2 + st.m2*(np.sin(x5))**2
        F1 = st.m1*np.sin(x3)*(st.g*np.cos(x3) - st.l1*x4**2)
        F2 = st.m2*np.sin(x5)*(st.g*np.cos(x5) - st.l2*x6**2)
        u = - F1 - F2 + u_lja*M + d0*x2 - (M1_star - d1*x4)*np.cos(x3)/st.l1 - (M2_star - d2*x6)*np.cos(x5)/st.l2

        return u


class SwingUpController(pm.Controller):
    """
    This class realise the swing up for equilibria with a arbitrary
    amount of turns of the pendulums

    The swing up of both pendulums require a adjustment of the
    integrator settings to
    rTol: 1e-09
    aTol: 1e-11
    """

    public_settings = OrderedDict([
        ("k", 10),
        ("long pendulum", "u"),
        ("short pendulum", "o"),
        ("poles", [-9, -7, -4, -2, -3, -2]),
        ("tick divider", 1)
    ])

    def __init__(self, settings):
        settings.update(input_order=0)
        settings.update(output_order=1)
        settings.update(input_type="system_state")
        self.module_settings = {"modules": settings["modules"]}
        pm.Controller.__init__(self, settings)

        # add dict with module information, because it was deleted in the base class
        settings.update(self.module_settings)
        settings["type"] = "LjapunovController"
        self.ljapunov = LjapunovController(settings)

        settings.update({"equilibrium": calc_equilibrium(settings)})
        settings.update(self.module_settings)
        settings["type"] = "LinearStateFeedback"
        self.linear_state_feedback = LinearStateFeedback(settings)

        self.switch = False

    def _control(self, time, trajectory_values=None, feedforward_values=None, input_values=None, **kwargs):
        x1, x2, x3, x4, x5, x6 = input_values

        # looking for the closest equilibrium
        eq_state = calc_closest_eq_state(self._settings, input_values)

        # we have to check several conditions
        #          phi1                  phi1_d
        a = (-0.2 + eq_state[2] <= x3 <= 0 + eq_state[2]) and (-0.2 <= x4 <= 0.5)
        #           phi2                 phi2_d
        b = (-0.2 + eq_state[4] <= x5 <= 0 + eq_state[4]) and (-0.2 <= x6 <= 0.5)
        #        phi1                  phi1_d
        c = (0 + eq_state[2] <= x3 <= 0.2 + eq_state[2]) and (-0.5 <= x4 <= 0.2)
        #          phi2                   phi2_d
        d = (0 + eq_state[4] <= x5 <= 0.2 + eq_state[4]) and (-0.5 <= x6 <= 0.2)

        eq_oo = False
        eq_ou = False
        eq_uo = False

        if self._settings["long pendulum"] == "o":
            eq_ou = True
        if self._settings["short pendulum"] == "o":
            eq_uo = True

        if eq_ou and eq_uo:
            eq_oo = True
            eq_ou = False
            eq_uo = False

        if (eq_oo and a and b)or (eq_oo and c and d) or (eq_ou and a) or (eq_ou and c) or (eq_uo and b) or (eq_uo and d):
            self.switch = True
        else:
            # this adjustment is only gut feeling
            e = (-0.3 + eq_state[2] <= x3 <= 0.3 + eq_state[2])
            f = (-0.3 + eq_state[4] <= x5 <= 0.3 + eq_state[4])
            if not (e and f):
                self.switch = False

        # print "t: ", t, "Switch: ", self.switch

        if self.switch:
            u = self.linear_state_feedback._control(time, trajectory_values,
                                                    input_values=input_values,
                                                    eq=eq_state)
        else:
            u = self.ljapunov._control(time, trajectory_values, input_values=input_values)

        return u


def calc_equilibrium(settings):
    equilibrium = np.zeros(6)
    if settings["long pendulum"] == "u":
        equilibrium[2] = np.pi
    if settings["short pendulum"] == "u":
        equilibrium[4] = np.pi

    return equilibrium


def calc_closest_eq_state(settings, state):
    # looking for the closest equilibrium for the two pendulums
    phi1 = float(state[2])
    phi2 = float(state[4])

    # consider the multiple pendulum states, because of the continuously angle
    # pendulum is on top: phi_eq = 2*PI*k
    # pendulum is at the bottom: phi_eq = (2*k + 1)*PI

    # pendulum 1 (long) is on top
    k1o = int(phi1/(2*np.pi))
    if (abs(phi1) % (2*np.pi)) > np.pi:
        k1o = k1o + np.sign(phi1)

    # pendulum 1 (long) is at the bottom
    k1u = int((phi1-np.pi)/(2*np.pi))
    if (abs(phi1 - np.pi) % (2*np.pi)) > np.pi:
        k1u = k1u + np.sign(phi1)

    # pendulum 2 (short) is on top
    k2o = int(phi2/(2*np.pi))
    if (abs(phi2) % (2*np.pi)) > np.pi:
        k2o = k2o + np.sign(phi2)

    # pendulum 2 (short) is at the bottom
    k2u = int((phi2 - np.pi)/(2*np.pi))
    if (abs(phi2 - np.pi) % (2*np.pi)) > np.pi:
        k2u = k2u + np.sign(phi2)

    eq_state = np.zeros(6)
    if settings["long pendulum"] == "o":
        eq_state[2] = 2*np.pi*k1o
    if settings["long pendulum"] == "u":
        eq_state[2] = (2*k1u + 1)*np.pi
    if settings["short pendulum"] == "o":
        eq_state[4] = 2*np.pi*k2o
    if settings["short pendulum"] == "u":
        eq_state[4] = (2*k2u + 1)*np.pi

    return eq_state


def calc_small_signal_state(settings, state):

    phi1 = (abs(state[2][0]) % (2*np.pi))*np.sign(state[2][0])
    phi2 = (abs(state[4][0]) % (2*np.pi))*np.sign(state[4][0])

    # transform the angle of the pendulums into an interval from -pi to +pi
    # pendulum 1 (long) is on top
    phi1_o = phi1
    if abs(phi1_o) > np.pi:
        phi1_o -= np.sign(state[2][0])*2*np.pi

    # pendulum 2 (short) is on top
    phi2_o = phi2
    if abs(phi2_o) > np.pi:
        phi2_o -= np.sign(state[4][0])*2*np.pi

    # transform the angle of the pendulums into an interval from 0 to 2pi
    # pendulum 1 (long) is at the bottom
    phi1_u = phi1
    if phi1_u < 0:
        phi1_u -= np.sign(state[2][0])*2*np.pi

    # pendulum 2 (short) is at the bottom
    phi2_u = phi2
    if phi2_u < 0:
        phi2_u -= np.sign(state[4][0])*2*np.pi

    # calc small signal state
    small_signal_state = np.zeros((6, 1))
    for idx, val in enumerate(state):
        small_signal_state[idx, 0] = val[0]

    if settings["long pendulum"] == "o":
        small_signal_state[2][0] = phi1_o - 0
    if settings["long pendulum"] == "u":
        small_signal_state[2][0] = phi1_u - np.pi
    if settings["short pendulum"] == "o":
        small_signal_state[4][0] = phi2_o - 0
    if settings["short pendulum"] == "u":
        small_signal_state[4][0] = phi2_u - np.pi

    return small_signal_state


class ModelPredictiveController(pm.Controller):
    """
    This class implements a model predictive controller.
    """

    public_settings = OrderedDict([
        ("X0", (0, 0, np.pi, 0, np.pi, 0)),
        ("U0", 0),
        ("Xref", (0, 0, 0, 0, 0, 0)),
        ("Xmin", [-1] + [None] * 5),
        ("Xmax", [2] + [None] * 5),
        ("Delta", .1),
        ("Steps", 50),
        ("tick divider", 1),
    ])

    def __init__(self, settings):
        settings.update(input_order=0)
        settings.update(output_dim=1)
        settings.update(input_type="system_state")
        self.module_settings = {"modules": settings["modules"]}
        pm.Controller.__init__(self, settings)

        x0 = np.array(self._settings["X0"])
        u0 = self._settings["U0"]
        x_ref = np.array(self._settings["Xref"])
        x_min = np.array(self._settings["Xmin"])
        x_min[np.equal(x_min, None)] = -np.inf
        x_max = np.array(self._settings["Xmax"])
        x_max[np.equal(x_max, None)] = np.inf

        Delta = self._settings["Delta"]
        Nt = self._settings["Steps"]
        Nx = 6
        Nu = 1
        Ns = Nx

        us = np.array([0])
        u_max = 1e3
        Dumax = np.array([1e3])

        # Also discretize using RK4.
        ode_rk4_casadi = mpc.getCasadiFunc(self.ode,
                                           [Nx, Nu],
                                           ["x", "u"],
                                           funcname="F",
                                           rk4=True,
                                           Delta=Delta,
                                           M=1)

        # Define stage cost and terminal weight.
        def lfunc(x, u, x_sp=None, u_sp=None):
            if x_sp is None:
                x_sp = np.zeros(x.shape)
            dx = (x - x_sp)
            # du = (u - u_sp)
            return mpc.mtimes(dx.T, dx)
            # return np.array([1])

        l = mpc.getCasadiFunc(lfunc,
                              [Nx, Nu, Nx],
                              ["x", "u", "x_sp"],
                              scalar=False,
                              funcname="l")

        def Pffunc(x, x_sp=None):
            if x_sp is None:
                x_sp = np.zeros(x.shape)
            dx = (x - x_sp)
            return 1e5 * mpc.mtimes(dx.T, dx)

        Pf = mpc.getCasadiFunc(Pffunc, [Nx, Nx], ["x", "x_sp"], funcname="Pf")

        def ef_func(x):
            dx = (x - x_ref)**2
            return dx

        ef = mpc.getCasadiFunc(ef_func, [Nx], ["x"], funcname="ef")

        sys = mpc.DiscreteSimulator(self.ode, Delta, [Nx, Nu], ["x", "u"])

        # First simulate to get a gue
        x = np.zeros((Nt+1, Nx))
        x[0,:] = x0
        u = np.zeros((Nt, Nu))
        for t in range(Nt):
            u[t, :] = u0
            x[t+1, :] = sys.sim(x[t, :], u[t, :])

        guess = dict()
        guess["x"] = x
        guess["u"] = u

        # build optimizer
        commonargs = dict(N={"x": Nx, "u": Nu, "t": Nt, # "ef": Ns
                             },
                          verbosity=3,
                          l=l,
                          x0=x0,
                          # guess=guess,
                          sp={"x": x_ref},
                          # ef=ef,
                          Pf=Pf,
                          lb={
                              "x": np.tile(x_min, (Nt + 1, 1)),
                              # "u": -u_max * np.ones((Nu,)),
                              # "Du": -Dumax,
                              "xf": x_ref,
                          },
                          ub={
                              "x": np.tile(x_max, (Nt + 1, 1)),
                              # "u": u_max * np.ones((Nu,)),
                              # "Du": Dumax,
                              "xf": x_ref
                          },
                          uprev=us,
                          funcargs={
                              "Pf": ["x", "x_sp"],
                              # "ef": ["x"]
                          }
                          )

        self.solver = mpc.nmpc(f=ode_rk4_casadi, **commonargs)

    @staticmethod
    def ode(q, u):
        dxdt = (q[1],
                u,
                q[3],
                st.g / st.l1 * np.sin(q[2])
                - st.d1 * q[3] / (st.m1 * st.l1**2)
                + np.cos(q[2])/st.l1 * u,
                q[5],
                st.g / st.l2 * np.sin(q[4])
                - st.d2 * q[5] / (st.m2 * st.l2**2)
                + np.cos(q[4])/st.l2 * u
                )
        return np.array(dxdt)

    def _control(self, time, trajectory_values=None, feedforward_values=None,
                 input_values=None, **kwargs):

        x = input_values

        self.solver.fixvar("x", 0, x)
        self.solver.solve()
        u = self.solver.var["u", 0, :]
        self.solver.par["u_prev", 0, :] = u

        return u

pm.register_simulation_module(pm.Controller, LinearStateFeedback)
pm.register_simulation_module(pm.Controller, LinearStateFeedbackParLin)
pm.register_simulation_module(pm.Controller, LinearQuadraticRegulator)
pm.register_simulation_module(pm.Controller, LjapunovController)
pm.register_simulation_module(pm.Controller, SwingUpController)
pm.register_simulation_module(pm.Controller, ModelPredictiveController)
