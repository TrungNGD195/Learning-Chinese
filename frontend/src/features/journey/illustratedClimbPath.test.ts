import {describe,expect,it} from 'vitest'
import {CLIMB_STATIONS,climbAction,climbGait,climbLocalProgress} from './illustratedClimbPath'

describe('shared painted climbing space',()=>{
  it('moves ground anchors up the stair view and changes horizontal direction around the bend',()=>{
    for(let i=1;i<5;i++)expect(CLIMB_STATIONS[i][1]).toBeLessThan(CLIMB_STATIONS[i-1][1])
    expect(CLIMB_STATIONS[4]).toEqual(CLIMB_STATIONS[5])
    expect(CLIMB_STATIONS[7]).toEqual(CLIMB_STATIONS[8])
    expect(CLIMB_STATIONS[6][0]).toBeLessThan(CLIMB_STATIONS[4][0])
    expect(CLIMB_STATIONS[10][0]).toBeGreaterThan(CLIMB_STATIONS[6][0])
  })
  it('keeps idle sprite phase deterministic and alternates footfalls with distance',()=>{
    expect(climbGait(.1)).toEqual(climbGait(.1))
    expect(climbGait(.1).frame).not.toEqual(climbGait(.2).frame)
    expect(climbGait(.1).lift).toBeCloseTo(0)
    expect(climbGait(.15).lift).toBeGreaterThan(.1)
    expect(climbGait(.2999999999999998)).toEqual(climbGait(.3))
  })
  it('keeps every footfall inside the painted walkable composition',()=>{
    for(const [u,v] of CLIMB_STATIONS){expect(u).toBeGreaterThan(.3);expect(u).toBeLessThan(.6);expect(v).toBeGreaterThan(.5);expect(v).toBeLessThan(1)}
  })
  it('retains the final arrival instead of wrapping the completed chapter to the base',()=>{
    expect(climbLocalProgress(15,15)).toBe(1)
    expect(climbLocalProgress(3.6,15)).toBeCloseTo(.6)
    expect(climbAction(.2)).toBe('climb')
    expect(climbAction(.6)).toBe('bend')
    expect(climbAction(.9)).toBe('gate')
  })
})
