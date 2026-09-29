"""Decision-independent, JSON-safe candle/candidate instrumentation."""
from collections import Counter, deque
from dataclasses import asdict
import math

STAGES = ('candles_evaluated','swing_candidates','historical_zones_available',
          'price_near_zone','fresh_enough_zone','zone_strength_passed','confirmation_passed',
          'market_structure_passed','entry_timing_passed','valid_stop_found',
          'valid_target_found','minimum_rr_passed','final_LONG_signals','final_SHORT_signals')


class Frame:
    def __init__(self,time,version):
        self.time=time; self.version=version
        self.funnel=Counter(candles_evaluated=1); self.rejections=Counter()
        self.rejected=[]; self.examples=[]; self.record=None

    def hit(self,key,count=1):
        self.funnel[key]+=count

    def candidate(self,direction,zone,entry,atr,context,close,stop=None,target=None):
        self.record=dict(timestamp=self.time,direction=direction,zone=asdict(zone),
            zone_midpoint=zone.midpoint,confirmation_close=close,entry_candidate=entry,
            distance_atr=abs(entry-zone.midpoint)/atr if atr>0 else None,atr=atr,
            stop_candidate=stop,target_candidate=target,rr=None,net_rr=None,
            market_structure=context,confirmation_type='None',primary_rejection_reason=None)
        if stop is not None and target is not None and entry!=stop:
            self.record['rr']=abs(target-entry)/abs(entry-stop)

    def reject(self,code):
        self.rejections[code]+=1
        if self.record is not None:
            self.record['primary_rejection_reason']=code
            self.rejected.append(self.record.copy())
            self.record=None

    def output(self):
        return dict(version=self.version,timestamp=self.time,funnel=dict(self.funnel),
                    rejections=dict(self.rejections),rejected_candidates=self.rejected)


class Accumulator:
    def __init__(self):
        self.funnel=Counter({s:0 for s in STAGES}); self.rejections=Counter()
        self.rejected=deque(maxlen=50); self.candles=[]

    def add(self,frame):
        if not frame:return
        self.funnel.update(frame.get('funnel',{})); self.rejections.update(frame.get('rejections',{}))
        self.rejected.extend(frame.get('rejected_candidates',[]))
        self.candles.append(dict(timestamp=frame.get('timestamp'),**frame.get('funnel',{})))

    def result(self):
        return dict(funnel=dict(self.funnel),rejections=dict(self.rejections.most_common()),
            rejected_candidates=list(self.rejected),per_candle=self.candles,
            counting_note='Zone stages count zone-candle candidates, not independent trades. Signals count selected directions per candle, even while another trade is open. Orders count executable flat-position actions. Swing/zone totals are observations across rolling prefixes, not unique identities.')
