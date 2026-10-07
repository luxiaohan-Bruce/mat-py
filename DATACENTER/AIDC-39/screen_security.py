"""Reproduce the static load-level screen; not a full dispatch benchmark."""
import json
import gurobipy as gp
from common import grid
from common.data import PACK, public_network, uc_parameters, nonislanding_contingencies, write_json
from common.validation import Checks, check_grid, check_uc


def screen():
    net=public_network()
    d=dict(network=net,T=1,dt_hours=.25,uc=uc_parameters(net),contingencies=nonislanding_contingencies(net))
    sites=[dict(bus=b,pcc_max_mw=200.) for b in [4,16,27]]
    with gp.Env(empty=True) as env:
        env.setParam('OutputFlag',0);env.start()
        with gp.Model(env=env) as m:
            m.Params.Threads=4;m.Params.Seed=1;m.Params.TimeLimit=600
            m.Params.FeasibilityTol=1e-8;m.Params.IntFeasTol=1e-8
            multiplier=m.addVar(lb=0,ub=1,name='background_load_multiplier')
            d['background_multiplier']=[multiplier]
            uc=grid.add_uc(m,d);pg=grid.add_dispatch(m,d,uc,'static')
            imp=m.addVars(3,1,lb=200,ub=200,name='full_site_import')
            network=grid.add_network(m,d,pg,imp,sites,'static',security=True)
            m.setObjective(multiplier,gp.GRB.MAXIMIZE);m.optimize()
            if m.Status!=gp.GRB.OPTIMAL:raise RuntimeError('Static screen did not reach optimum')
            maximum=multiplier.X
            schedule=grid.dispatch_solution(pg,network,d)
            schedule.update(uc=grid.uc_solution(uc,d),imports_mw=grid.values(imp,3,1),checked_contingencies=d['contingencies'])
            d['background_multiplier']=[maximum]
            checks=Checks();status,_=check_uc(checks,d,schedule['uc'])
            check_grid(checks,d,schedule,status,sites,security=True)
            certificate=checks.finish({}, {})
            result=dict(kind='static_preventive_load_maximization',maximum_background_multiplier=maximum,
                        n_contingencies=len(d['contingencies']),site_imports_mw=[200,200,200],
                        generator_assumption='All ten original generators online; synthetic UC Pmin; no intertemporal ramp',
                        source_sha256=net['source_sha256'],objective_bound=m.ObjBound,
                        verification=certificate,schedule=schedule)
            if not certificate['passed']:raise RuntimeError(certificate['violations'])
            write_json(PACK/'source/static_security_screen.json',result)
            print(json.dumps({k:result[k] for k in ['maximum_background_multiplier','n_contingencies']}))
            return result


if __name__=='__main__':screen()
