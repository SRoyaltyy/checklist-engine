import csv,collections
U=(1,2,3,5,10,20);B=(3,5,10,20,60,120);CAP=300
def tfok(u,b,short):
  if u*b>CAP: return f"invalid: {u*b}d window + 250d baseline > ~550d warm-up budget; leaves too little of 2020-22 to learn on"
  if b<10 and not(short and u<=2): return "invalid: <10 bars cannot show a path"
  return ""
LEAK="answer(D) uses only bars dated < D; indicator warm-up and 250-bar baseline also < D; events keyed on publication date < D"
# facet = (name, kind, definition, answers, formula, short)
F=lambda *a:a
# generic line facets for an indicator line X (oscillators/flows)
def line(X,zone):
  return [F("path_dir","directional",f"{X} OLS slope across window","{rising,falling,flat}","sign of slope, |t|>2"),
   F("zone_route","zone_transition",f"{X} zone at window start -> zone at end",f"{{{zone}}} start->end pairs (9)","zone(first bar) , zone(D-1)"),
   F("cross_event","crossover",f"{X} crossed its midline/signal in window","{up,down,both,none}","sign change"),
   F("price_divergence","divergence",f"Price swing vs {X} swing disagree","{bull,bear,none}","2 pivot lows/highs in window, strict pivot rule"),
   F("time_in_zone","persistence",f"Share of window bars in each {X} zone",f"{{mostly_high,mostly_low,mostly_mid,mixed}}",">60% rule"),
   F("speed","acceleration",f"{X} change in last third vs first third","{speeding_up,slowing_down,steady}","|Δ3|/|Δ1| >1.5/<0.67"),
   F("vs_own_past","character",f"{X} window range vs its own prior 250-bar ranges (merged vs_usual/regime_rank)","{wider,usual,narrower}","percentile >80/<20")]
PIV="pivot=bar whose H(L) is strict max(min) of ±k bars, k=max(2,N//10); confirmed only k bars later and still < D"
T={}
def add(t,v,fs,units=U,lbs=B,note="",opt=""):T.setdefault(t,[]).append((v,fs,units,lbs,note,opt))
add("candles","OHLC",[
 F("intraday_change","directional","Mean (C-O)/O across window","{up>1%,down<-1%,flat}","mean((C-O)/O)",1),
 F("interday_change","momentum","Close-to-close change across window","{up>5%,flat,down>5%}","C[-1]/C[0]-1"),
 F("overnight_vs_intraday","decomposition","Compounded share of window move from overnight gaps vs intraday (merged #9, taskforce_BE_TER)","{up_move,down_move}x{gap_driven,intraday_driven,mixed}","sum ln(O/Cprev) vs sum ln(C/O)",1),
 F("gap_up","event","Gap up (O>prev H) in window, and fate","{filled,open,none}","filled if later L<=H_prev before D",1),
 F("gap_down","event_down","Gap down (O<prev L) in window, and fate","{filled,open,none}","filled if later H>=L_prev before D",1),
 F("pattern_1d_mix","pattern","Which 1-bar pattern family dominates the window","{bull_reversal(hammer),bear_reversal(shooting_star),indecision(doji/spinning),trend(marubozu),none}","TA-Lib counts; most frequent family",1),
 F("pattern_2d_mix","pattern_pair","Which 2-bar pattern family dominates","{bull(engulf/harami/piercing),bear(engulf/harami/dark_cloud),none}","TA-Lib counts",1),
 F("pattern_3d_seen","pattern_triple","Latest 3-bar pattern seen anywhere in window, and its position","{3ws,3bc,morning_star,evening_star}x{early,late}+none","TA-Lib",1),
 F("cup_handle","shape","Strict cup-and-handle: yes/no","{yes,no}",PIV+"; lip pivots L1,L2 within 3%; cup low ≥15% below lips & ≥N/3 bars wide; handle after L2 retraces 20-50% of cup depth on lower volume"),
 F("flag","shape_flag","Strict flag: yes/no and direction","{bull,bear,none}",PIV+"; pole move ≥3 ATR in ≤N/4 bars; then ≥2 pivot highs and ≥2 pivot lows in parallel channel (slope diff <25%) against pole, retrace ≤50%"),
 F("inside_outside","range_sequence","Sequence of inside/outside bars","{inside_cluster>=2,outside_after_inside,mostly_outside,none}","H<Hprev&L>Lprev etc",1),
 F("red_green_balance","balance","Sum green bodies / sum red bodies","{green>1.5,red<0.67,even}","",1),
 F("last_green_vs_red","balance_last","Latest green body vs latest red body within window","{green_bigger,red_bigger,similar}","1.25x",1),
 F("wick_body","pushback","Mean (upper-lower wick)/range","{upper_dominant,lower_dominant,balanced}","±0.15",1),
 F("close_location_route","close_location","Close location in own day range followed over the route","{near_high_mostly,near_low_mostly,mixed}x{improving,worsening,steady}","mean (C-L)/(H-L) and its slope",1),
 F("wick_evolution","wick_trend","Wicks lengthening and bodies shrinking near the window extreme","{lower_wicks_longer_near_low,upper_wicks_longer_near_high,bodies_shrinking_near_extreme,none}","last 5 bars before extreme vs window mean",1),
 F("size_vs_chart","relative_size","Mean body vs all prior history","{larger,similar,smaller}","1.25/0.8",1),
 F("run_structure","run","Longest green run vs longest red run inside window","{green_longer,red_longer,equal}","run lengths",1),
 F("run_biggest_move","run_extreme","Biggest body inside the longest run vs ATR14","{big>1.5ATR,normal,small}","",1),
 F("run_history","chain_history","Own-history green vs red runs (avg length & size, prior 500 bars)","{green_longer_bigger,red_longer_bigger,mixed}",""),
 F("run_unusual","chain_anomaly","Longest window run vs own run distribution","{unusual>90pct,typical}","percentile",1),
 F("down_vs_up_moves","asymmetry","Avg down-bar size vs up-bar size","{downs_bigger,ups_bigger,equal}","1.2x",1)])
add("volume","RVOL20",[
 F("trend","directional","RVOL slope","{rising,falling,flat}",""),
 F("spike","event","Any bar >3x 50-bar median (spike lives here only)","{yes_early,yes_late,no}","",1),
 F("dry_up_at_low","location","Volume dry-up (<0.6x med50) at the window lowest close, or mirror at its highest close","{at_low,at_high,both,none}","",1),
 F("price_confirm","divergence","Volume trend agrees with price trend","{confirm,diverge,neutral}",""),
 F("vs_own_past","character","Window mean vs own 250-bar mean","{high,normal,low}","1.5/0.67"),
 F("spike_then","sequence","What price did after the spike","{continued,reversed,no_spike}",""),
 F("max_vol_position","time_location","Where the window max-volume bar sits","{start,middle,at_price_low,end}","argmax(V) position in thirds; at_price_low if within 2 bars of argmin(C)",1),
 F("segment_compare","segment_compare","Mean volume in the decline segment vs the rally segment (split at window low)","{rally_heavier,decline_heavier,similar}","1.25x; segments split at argmin(C)")],opt="RVOL10/50 optional")
add("volume","dollar_volume",[
 F("trend","directional","Dollar volume slope","{rising,falling,flat}",""),
 F("liquidity_tier_route","zone_transition","Liquidity tier start->end","{<1M,1-10M,>10M} pairs",""),
 F("consistency","persistence","Share of days >$1M","{all,most,few}",""),
 F("concentration","balance","Top-3 days share of window $vol","{concentrated>50%,spread}",""),
 F("speed","acceleration","Last third vs first third","{speeding_up,slowing_down,steady}",""),
 F("vs_own_past","character","Vs own 250-bar mean","{high,normal,low}","")])
add("volume","up_down_volume",[
 F("dominance","balance","sumV up bars / sumV down bars","{up_heavy>1.3,down_heavy<0.77,even}",""),
 F("trend","directional","Up/down volume ratio trend along the route (accumulation vs distribution during the move; overlaps OBV/AD slope, kept here)","{improving(accumulation),worsening(distribution),flat}","ratio 2nd half vs 1st half"),
 F("price_divergence","divergence","Down-heavy volume while price rises (or reverse)","{bull,bear,none}",""),
 F("flip","crossover","Dominance flipped in window","{to_up,to_down,none}",""),
 F("run","run","Longest run of up-heavy 5-bar blocks","{long,short}",""),
 F("vs_own_past","character","Ratio vs own history","{unusual_up,unusual_down,typical}","")])
for v in ("OBV","AD_line","MFI14"):
  add("volume",v,line(v,"high,mid,low"),note="MFI zones 80/20; OBV/AD zones = percentile of own 250 bars")
add("volume","VWAP_anchored",[
 F("above_share","persistence","Share of bars closing above VWAP anchored at window start","{mostly_above,mostly_below,mixed}",""),
 F("cross","crossover","Crossed anchored VWAP","{up,down,both,none}",""),
 F("distance_route","stretch","Distance/ATR start->end","{stretching,reverting,stable}",""),
 F("reclaim","event","Lost then reclaimed VWAP","{yes,no}",""),
 F("slope","directional","VWAP slope","{up,down,flat}",""),
 F("tests","interaction","Touches of VWAP from either side that held","{support_held,resistance_held,broke,none}","")])
add("volume","volume_profile",[
 F("poc_route","zone_transition","Price vs point-of-control start->end","{below,at,above} pairs","POC=price bin with max volume in window"),
 F("value_area_share","persistence","Share of bars inside 70% value area","{mostly_inside,mostly_outside}",""),
 F("hvn_test","interaction","Tested high-volume node and held/broke","{held,broke,none}",""),
 F("lvn_crossing","event","Price crossed a low-volume node fast (≤2 bars)","{yes,no}",""),
 F("poc_migration","directional","POC of 2nd half vs 1st half","{up,down,same}",""),
 F("profile_shape","shape","Profile shape","{P,b,D,double}",""),
 F("overhead_supply","supply","Share of window volume traded above current price (mirror: below = support)","{above>60%,30-60%,<30%}","volume-at-price bins of window"),
 F("holder_cost","holder_cost","Share of window volume (holders proxy) at a loss vs in profit","{most_at_loss,most_in_profit,split}","VAP above vs below C[-1]")])
MA=[F("above_share","persistence","Share of bars closing above MA","{mostly_above,mostly_below,mixed}","",1),
 F("fresh_cross","crossover","Close crossed MA in window","{up,down,both,none}","",1),
 F("cross_count","cross_frequency","Number of times price crossed the MA in window","{0,1-2,3-5,6+}","count sign changes of C-MA"),
 F("slope","directional","MA slope","{up,down,flat}","±1%"),
 F("distance_route","stretch","(C-MA)/ATR start->end","{stretching,reverting,stable}",""),
 F("tests","interaction","Touches of MA from either side: support held / resistance held / broke","{support_held,resistance_held,broke,none}",""),
 F("speed","acceleration","Slope last third vs first third","{speeding_up,slowing_down,steady}",""),
 F("touch_order","touch_sequence","First touch of a rising MA vs later touches (mirror: falling MA from below)","{rising:first_held,rising:later_held,rising:broke,falling:first_rejected,falling:later_rejected,falling:reclaimed,none}","touch numbering since MA slope turned")]
for v in ("SMA20","SMA50","SMA200","EMA21"):
  add("moving_averages",v,MA,opt="SMA10/80, EMA9/50 optional (size-only)")
add("moving_averages","MA_group(10/20/50/200)",[
 F("bunching_route","compression","MA bunching/stretch: spread of SMA5..SMA30 / ATR14, start->end, and end vs own history with sign (merged case_chart7 stretch)","{tight<1ATR,mid,wide>3ATR} pairs x{stretched_up>90pct,stretched_down>90pct,normal}","(max-min of SMA5,10,20,30)/ATR14"),
 F("stack_route","zone_transition","Strict stack state start->end","{full_bull,partial_bull,partial_bear,full_bear(reversed)} pairs","full = all 4 MAs in order; partial = ≥2 adjacent pairs in order"),
 F("days_since_partial_flip","timing","Bars since the stack last changed state","{<5,5-20,>20,none}","",1),
 F("stack_flip","event","Golden/death cross in window","{golden,death,none}",""),
 F("time_bull_stack","persistence","Share of bars bull-stacked","{most,some,none}",""),
 F("fan_out","acceleration","Spread change last third vs first","{fanning,converging,steady}",""),
 F("deepest_pullback_ma","pullback_depth","Deepest pullback in window, by which MA its low touched","{MA10,MA20,MA30,broke_MA30,none}","min over pullbacks of L vs SMA10/20/30 (touch = L<=MA); broke = close<MA30"),
 F("full_stack_streak","run","Longest run of consecutive bars in full bull order and in full bear order (merged case_chart5 bear days)","{bull,bear}x{0,1-4,5-19,20+}","consecutive count"),
 F("bounce_ceiling","ceiling","Which MA the bounce stalled under, plus consecutive bounces failing below MA30 (mirror of deepest_pullback_ma)","{under_MA10,under_MA20,under_MA30,above_MA30}x{fails_0,1,2+}","bounce high vs SMA10/20/30"),
 F("price_inside","location_share","Share of bars with close between fastest and slowest MA","{mostly_inside,mostly_outside}","")])
add("range_position","Bollinger20_2",[
 F("zone_route","zone_transition","%B zone start->end","{top,mid,bottom} pairs",""),
 F("band_walk","run","≥3 bars at/beyond a band (Bollinger only)","{upper,lower,none}","",1),
 F("reentry","event","Re-entered after excursion","{from_below,from_above,none}","",1),
 F("time_upper","persistence","Share of bars %B>0.5","{upper,lower,balanced}",""),
 F("pctb_path","directional","%B slope","{rising,falling,flat}",""),
 F("width_route","compression","Band width start->end","{squeezing,widening,stable}","")])
add("range_position","Fibonacci_swing",[
 F("level_held","level","Deepest retracement level touched and held (Fib only)","{23.6,38.2,50,61.8,78.6,broken}","swing from strict pivots in window"),
 F("retrace_route","zone_transition","Retracement zone start->end","{shallow,mid,deep} pairs",""),
 F("ext_reached","event","Hit 127/161.8 extension","{yes,no}",""),
 F("level_touches","interaction","Touches of 61.8 that held","{0,1,2+}",""),
 F("swing_dir","directional","Swing direction","{up_swing,down_swing}",""),
 F("time_below_50","persistence","Share of bars below 50% level","{most,some,none}","")])
for v,nt in (("Donchian20","channel = max H/min L of prior 20 bars"),("HiLo_window","range = window high/low")):
  add("range_position",v,[
   F("zone_route","zone_transition","Position in channel start->end","{top,mid,bottom} pairs",nt),
   F("breakout","event","Close beyond channel","{up,down,none}","",1),
   F("time_top","persistence","Share of bars in top third","{most,some,none}",""),
   F("width_route","compression","Channel width start->end","{narrowing,widening,stable}",""),
   F("midline_cross","crossover","Crossed channel midline","{up,down,both,none}",""),
   F("failed_break","sequence","Broke out then closed back inside","{bull_trap,bear_trap,none}","")])
add("extremes","new_highs_lows",[
 F("new_extreme","event","Made new 60-bar high/low in window","{high,low,both,none}",""),
 F("swing_count","structure","Counts of higher lows and lower highs among strict pivots, and breaks of the HL pattern (merged HL/LH count)","{HL_0,HL_1-2,HL_3+}x{LH_0,LH_1-2,LH_3+}x{breaks_0,breaks_1+}",PIV+"; break = pivot low below prior pivot low after ≥2 HL"),
 F("time_since","timing","Bars since last new high, as share of window","{recent,mid,old,none}",""),
 F("count","run","Number of new highs","{0,1-2,3+}",""),
 F("high_then_low","sequence","Order of window high and low","{high_first,low_first}",""),
 F("giveback","recovery","Share of the prior rise, spike or whole run given back by D-1 (mirror = recovery facet in drawdown)","{none<10%,partial,most>60%}x{last_rise,spike,whole_run}","(peak-C[-1])/(peak-launch low)"),
 F("follow_through","confirmation","After new high, closed higher within 3 bars","{yes,no,no_new_high}",""),
F("hl_base_breakout","breakout_base","Close above window high after a higher-low base (mirror: close below window low after lower-high top); bars from HL to breakout; RSI6/12/24 (Webull RSI1/2/3) all >70 (mirror <30) on that day","{up,down}x{<5,5-20,>20 bars}x{rsi_all3_extreme,not}+none",PIV)],units=(1,2,3,5))
add("extremes","drawdown",[
 F("depth","magnitude","Max drawdown/ATR","{shallow<2,mid,deep>5}",""),
 F("recovery","recovery","Share of the prior drop recovered by D-1","{full,partial,none}",""),
 F("recovery_speed","acceleration","Bars to recover half vs bars to fall","{faster,slower,not_yet}",""),
 F("vs_own_past","character","Depth vs own past drawdowns (500 bars)","{unusual,typical,small}",""),
 F("count","run","Separate ≥2ATR drawdowns in window","{0,1,2+}",""),
 F("shape","shape","Drop shape","{V,U,staircase}",""),
 F("second_leg","second_leg","(Mirrored) New low after bouncing ≥X% off the prior low; bounce size bucket","{down:new_low_after_bounce,up:new_high_after_pullback}x{bounce5-10%,10-25%,>25%}+none","prior low = strict pivot low; bounce = max C after it / low -1"),
 F("capitulation_bar","capitulation","Last capitulation bar (range>3 ATR, close bottom 20%, RVOL>3) or mirror blow-off bar (close top 20%) still in window: age and size","{capitulation,blowoff}x{age<5,5-20,>20}x{3-5ATR,>5ATR}x{record_vol,not_record}x{close_near_far_end,close_mid,long_reversal_wick}+none",""),
 F("second_low_volume","retest_volume","Volume at the second low vs the capitulation bar (mirror: second high vs blow-off)","{lower,higher,no_second_test}","V(second pivot)/V(capitulation)"),
 F("move_duration","duration","Duration of the decline (mirror: of the advance) from last opposite strict pivot","{down,up}x{<10,10-40,>40 days}",PIV),
 F("climax_context","trend_context","Where the capitulation/blow-off sits in the trend, combined with shock vs worn-out (one large fresh overnight gap vs long intraday bleed)","{after_single_sharp_move,end_of_long_trend(>=60 bars),mid_trend,none}x{fresh_overnight_shock,long_intraday_bleed}","trend length = bars since last opposite strict pivot")],units=(1,2,3,5))
add("extremes","big_picture",[
 F("multi_year_position","location","Position of window end in the 1y, 2y and 3y range (2y = taskforce_BE_TER)","{1y,2y,3y}x{top_quartile,mid,bottom_quartile}","bars < D"),
 F("weekly_trend","directional","Weekly close slope over the window","{rising,falling,flat}","weekly bars from daily < D"),
 F("dist_from_high","stretch","Distance from all-time (from listing) and 3y high (mirror: from 3y low)","{from_ath,from_3y_high,from_3y_low}x{<10%,10-50%,>50%}",""),
 F("ath_age","timing","Bars since all-time high (mirror: all-time low)","{high,low}x{<60,60-250,>250}",""),
 F("weekly_stack","structure","Weekly 10/40 MA order","{bull,bear,mixed}",""),
 F("range_route","zone_transition","3y-range tercile start->end","{low,mid,high} pairs","")],units=(5,10,20),note="needs up to 756 bars of history before D: for 2020-22 dates ATH/3y facets are truncated (flag history_short)")
BASE="flat base = ≥10 bars with (max H-min L) ≤2 ATR, ending before run start; run start = first close above base high; all < D"
add("extremes","base_and_run",[
 F("run_multiple","magnitude","How many times its base price the run reached (peak/base mean close)","{<1.5x,1.5-3x,>3x,no_base_run}",BASE),
 F("round_trip","round_trip","Price returned to the launch base","{back_in_base,above_base,below_base,no_base_run}",BASE),
 F("first_ma20_touch","timing","Bars from run start to first SMA20 touch","{not_yet,<5,5-20,>20,no_base_run}","touch = L<=SMA20"),
 F("vol_vs_base","base_relative","Peak-run volume vs the quiet base's average volume (not RVOL20)","{>10x,3-10x,<3x,no_base_run}","max V(run)/mean V(base)"),
 F("base_tightness","compression","Base range / ATR","{tight<1,normal1-2,no_base}",BASE),
 F("run_length","run","Bars from run start to peak","{<5,5-20,>20,no_base_run}",""),
 F("at_launch_shelf","shelf_return","Back at the launch shelf of the last leg (mirror: breakdown shelf of last down leg)","{up:at_shelf,up:above,up:below,down:at_shelf,down:below,down:above,no_leg}","shelf = staircase shelf preceding leg"),
 F("peak_volume","climax_volume","Volume at the final high vs the run max volume (mirror: final low of a down run)","{is_max,50-100%,<50%,no_run}","V(argmax C)/max V(run)"),
 F("parabolic_reversal_day","reversal_bar","After a parabolic run: gap up, close near low, record volume on red (mirror: after a crash, gap down, close near high, record volume on green)","{top_reversal,bottom_reversal}x{age<5,5-20,>20}+none","record = max V in prior 250 bars; near = close in far 25% of range"),
 F("rehearsal","rehearsal","Earlier smaller climax bar in the same run led to a pause, not the end (mirror: smaller capitulation in a decline)","{up:rehearsal_paused,down:rehearsal_paused,none}","smaller climax = RVOL>2 & range>2ATR before the largest")],units=(1,2),note="mirrored: runs down from a base use the same facets with down: prefix; GLND/VSTS/GME/BB/UP/AAPL screenshots are 2025-26: idea source only, never for thresholds")
add("extremes","52w_range",[
 F("dist_route","zone_transition","Distance-to-52w-high bucket start->end","{near<5%,mid,far>30%} pairs",""),
 F("touch_52w","event","Touched 52w high/low","{high,low,none}",""),
 F("closing_speed","acceleration","Gap to 52w high closing faster/slower","{faster,slower,steady}",""),
 F("rejection","interaction","Touched then fell ≥2ATR","{yes,no}",""),
 F("position_share","persistence","Share of bars in top quartile of 52w range","{most,some,none}",""),
 F("range_width","relative_size","52w range width vs median stock","{wide,normal,narrow}","")],units=(1,2,3,5),note="needs 252 daily bars < D")
add("overbought_oversold","RSI6",line("RSI6","ob>70,mid,os<30")+[F("exit_os","event","Left oversold/overbought zone","{exit_os,exit_ob,none}","",1),
 F("rsi_floor","floor","Minimum RSI6 in window","{<30,30-40,40-50,>=50}","min(RSI6)"),
 F("rsi_ceiling","ceiling_osc","Maximum RSI6 in window (mirror of rsi_floor)","{>70,60-70,50-60,<=50}","max(RSI6)"),
 F("extreme_position","time_location","Where RSI max and min sit in the window","{max_early_min_late,min_early_max_late,both_early,both_late}","argmax/argmin position, halves")],opt="Webull RSI1/2/3 = RSI6/12/24")
add("overbought_oversold","RSI12",line("RSI12","ob>70,mid,os<30")+[F("exit_os","event","Left oversold/overbought zone","{exit_os,exit_ob,none}","",1),
 F("rsi_floor","floor","Minimum RSI12 in window","{<30,30-40,40-50,>=50}","min(RSI12)"),
 F("rsi_ceiling","ceiling_osc","Maximum RSI12 in window (mirror of rsi_floor)","{>70,60-70,50-60,<=50}","max(RSI12)"),
 F("extreme_position","time_location","Where RSI max and min sit in the window","{max_early_min_late,min_early_max_late,both_early,both_late}","argmax/argmin position, halves"),
 F("length_fan","multi_length_order","RSI6/12/24 order across the window, and bunched vs fanned (merged case_chart1 item 4; agreement facet, extra lengths not counted)","{fast>mid>slow,slow>mid>fast,mixed}x{bunched,fanned}","order share >60% of bars; bunched = mean(max-min of the 3) <5 RSI pts")],opt="Webull RSI1/2/3 = RSI6/12/24")
add("overbought_oversold","RSI24",line("RSI24","ob>70,mid,os<30")+[F("exit_os","event","Left oversold/overbought zone","{exit_os,exit_ob,none}","",1),
 F("rsi_floor","floor","Minimum RSI24 in window","{<30,30-40,40-50,>=50}","min(RSI24)"),
 F("rsi_ceiling","ceiling_osc","Maximum RSI24 in window (mirror of rsi_floor)","{>70,60-70,50-60,<=50}","max(RSI24)"),
 F("extreme_position","time_location","Where RSI max and min sit in the window","{max_early_min_late,min_early_max_late,both_early,both_late}","argmax/argmin position, halves")],opt="Webull RSI1/2/3 = RSI6/12/24")
add("overbought_oversold","RSI14",line("RSI14","ob>70,mid,os<30")+[F("exit_os","event","Left oversold/overbought zone","{exit_os,exit_ob,none}","",1),
 F("rsi_floor","floor","Minimum RSI14 in window","{<30,30-40,40-50,>=50}","min(RSI14)"),
 F("rsi_ceiling","ceiling_osc","Maximum RSI14 in window (mirror of rsi_floor)","{>70,60-70,50-60,<=50}","max(RSI14)"),
 F("extreme_position","time_location","Where RSI max and min sit in the window","{max_early_min_late,min_early_max_late,both_early,both_late}","argmax/argmin position, halves")],opt="extra variant (classic length)")
add("overbought_oversold","Stoch14_3",line("Stoch","ob>80,mid,os<20"))
add("overbought_oversold","WilliamsR14",line("W%R","ob>-20,mid,os<-80"),note="near-dup of Stoch (same math, inverted): optional")
add("momentum","MACD12_26_9",line("MACD hist","pos,neutral,neg"),opt="MACD5_35_5 optional")
add("momentum","ROC20",line("ROC20","pos>5%,flat,neg<-5%")+[F("length_fan","multi_length_order","ROC5/20/60 order across the window (agreement facet)","{fast>mid>slow,slow>mid>fast,mixed}","order share >60%")],opt="ROC5/60 optional")
add("momentum","ADX14",[
 F("trend_strength_route","zone_transition","ADX zone start->end","{trending>25,weak,none<15} pairs",""),
 F("di_cross","crossover","+DI/-DI cross","{bull,bear,none}",""),
 F("adx_slope","directional","ADX slope","{rising,falling,flat}",""),
 F("peak_turn","event","ADX peaked and turned down","{yes,no}",""),
 F("time_trending","persistence","Share of bars ADX>25","{most,some,none}",""),
 F("speed","acceleration","ADX change last third vs first","{speeding,slowing,steady}","")])
add("momentum","Ichimoku",[
 F("cloud_route","zone_transition","Price vs cloud start->end","{above,in,below} pairs","cloud shifted 26 bars uses only past data"),
 F("tk_cross","crossover","Tenkan/Kijun cross","{bull,bear,none}",""),
 F("cloud_twist","event","Span A/B twist","{bull,bear,none}",""),
 F("time_above","persistence","Share of bars above cloud","{most,some,none}",""),
 F("chikou_route","directional","Lagging span vs price 26 bars ago, start->end","{improving,worsening,same}",""),
 F("kijun_tests","interaction","Touches of Kijun that held","{support_held,resistance_held,broke,none}","")],units=(1,2,3,5))
add("volatility","ATR14",[
 F("trend","directional","ATR% slope","{expanding,contracting,flat}",""),
 F("vs_own_past","character","ATR% vs own 250 bars (merged vs_usual/regime_rank)","{high,normal,low}",""),
 F("shock","event","Biggest bar range vs own usual range (median 250-bar range), and when","{3-5x,>5x}x{early,late}+none","max(H-L)/median250(H-L)",1),
 F("vol_direction_link","divergence","Vol rises on down moves vs up","{down_vol,up_vol,neutral}",""),
 F("route","zone_transition","Vol tercile start->end","{low,mid,high} pairs",""),
 F("speed","acceleration","Last third vs first third","{speeding,slowing,steady}",""),
 F("range_max_position","time_location","Where the widest-range bar sits","{start,middle,end}","argmax(H-L) in thirds"),
 F("segment_compare","segment_compare","Range at the window peak vs now (last 20%)","{expanded,contracted,similar}","mean(H-L) around argmax(C) vs last 20%"),
F("range_calming","range_route","Range calming/expanding after a crash (mirror: after a spike): ATR of last 20 vs first 20 bars","{after_crash,after_spike}x{calming<0.7,steady,expanding>1.3}+none","ATR14(last20)/ATR14(first20)")])
add("volatility","squeeze(BB_in_Keltner)",[
 F("state_route","zone_transition","Squeeze state start->end","{in,out} pairs",""),
 F("release_dir","event","Squeeze released, direction","{up,down,none}",""),
 F("duration","run","Longest squeeze run","{long>=10,short,none}",""),
 F("time_in","persistence","Share of bars in squeeze","{most,some,none}",""),
 F("release_volume","confirmation","Breakout-day volume vs average volume during the squeeze","{>3x,1.5-3x,<1.5x,no_release}","V(release)/mean(V in squeeze)"),
 F("release_gap","gap_vs_width","Gap out of the squeeze, sized vs squeeze width","{gap>1x_width,gap<1x_width,no_gap,no_release}","|O-Cprev|/(BB width at release)"),
 F("release_close_location","close_location","Where the breakout day closed in its own range","{top_third,middle,bottom_third,no_release}","(C-L)/(H-L)"),
 F("vs_own_past","character","Squeeze length vs own past squeezes","{long,typical}","")])
add("relative_strength","vs_SPY",None)
for v,n in (("vs_SPY","SPY"),("vs_sector_peers","sector median; sector = current label (no D-1 sector history for 2020-24 on box; see sector_source). Option: SEC SIC code from latest filing before D as dated sector source - coverage untested"),("vs_theme_peers","theme = correlation cluster fit on 250 bars < D, refit monthly")):
  T["relative_strength"]=[x for x in T.get("relative_strength",[]) if x[1]]
  add("relative_strength",v,[
   F("rs_trend","directional","RS line slope","{out,under,flat}",n),
   F("rs_new_high","event","RS line window high","{yes,no}",""),
   F("divergence","divergence","Stock falls while bench rises (or reverse)","{bull,bear,none}",""),
   F("rank_route","zone_transition","Peer-percentile quartile start->end","{q1..q4} pairs",""),
   F("beta_shift","second_order","Rolling beta change","{rising,falling,flat}",""),
   F("down_day_resilience","balance","Share of bench down days outperformed","{high,low,mid}",""),
   F("speed","acceleration","RS slope last third vs first","{speeding,slowing,steady}",""),
   F("leg_attribution","attribution","Share of the latest leg explained by the bench (beta-adjusted, beta from 250 bars < window)","{up_leg,down_leg}x{mostly_bench>60%,mixed,mostly_own<30%}","beta*bench_ret/stock_ret over leg"),
   F("own_vs_bench_days","day_attribution","Share of down days (mirror: up days) that were stock-specific (bench flat or opposite) vs bench-wide","{down_days,up_days}x{mostly_own,mixed,mostly_bench}","own = |bench ret|<0.3% or opposite sign"),
   F("turn_sync","turn_sync","Did the bench bottom (mirror: top) within N bars of the stock's turn","{bottom,top}x{bench_first,together(+-N/10),stock_first,bench_no_turn}",PIV)])
add("support_resistance","prior_pivots",[
 F("approach_route","stretch","Distance to nearest level start->end","{approaching,leaving,stable}",PIV),
 F("current_level_touches","run","Prior touches of the current price level (±0.5 ATR) in window, and their fate","{none,1-2_held,3+_held,broke_up_after_1-2,broke_up_after_3+,broke_down_after_1-2,broke_down_after_3+}","touch = H or L within band; held if close reversed ≥1 ATR within 3 bars",1),
 F("break_status","event","Broke a level","{up,down,none}",""),
 F("retest","interaction","Retest of broken level","{held,failed,none}",""),
 F("bounce_strength","acceleration","Each bounce bigger or smaller","{stronger,weaker,one_only}",""),
 F("level_cluster","structure","≥2 levels within 1 ATR","{yes,no}","")])
add("support_resistance","old_ranges_breakdowns",[
 F("inside_old_range","location","Price inside a prior consolidation range (≥15 bars, range ≤3 ATR, ended before window)","{inside,above,below,none}","ranges found from bars < window start"),
 F("at_breakdown_level","level","Price within 0.5 ATR of a prior breakdown level (close below range low on RVOL>1.5)","{at,below,above,none}",""),
 F("approach_route","stretch","Moving toward or away from the nearest landmark","{approaching,leaving,stable}",""),
 F("reaction","interaction","Reaction on reaching the landmark","{rejected,accepted,not_reached}",""),
 F("landmark_age","timing","Age of nearest landmark","{<60,60-250,>250 bars}",""),
 F("landmark_count","run","Landmarks within 2 ATR","{0,1,2+}","")],units=(1,2,3,5))
add("support_resistance","unfilled_gaps",[
 F("gap_side","location","Open gaps above/below","{above,below,both,none}",""),
 F("approach_route","stretch","Moving toward nearest gap","{approaching,leaving,stable}",""),
 F("partial_fill","event","Gap-fill progress of nearest open gap","{0-25%,25-75%,>75%,filled}x{gap_above,gap_below}","share of gap distance retraced"),
 F("leg_start_gap","leg_gap","Gap that started the latest leg (down or up): age, and whether price is still beyond the gap edge","{down_leg,up_leg}x{age<5,5-20,>20}x{still_beyond,back_through}+none","leg = move >=3 ATR from a strict pivot; gap = first gap of the leg"),
 F("first_bounce_winback","winback","Share of a gap-down won back by the first bounce (mirror: gap-up given back by the first dip)","{gap_down_won_back,gap_up_given_back}x{>75%,25-75%,<25%}+none",""),
 F("gap_age","timing","Age of nearest open gap","{<20,20-60,>60 bars}",""),
 F("gap_count","run","Open gaps left behind, by side (merged #7)","{above,below}x{0,1,2+}",""),
 F("respect","interaction","Price reversed at gap edge","{yes,no}","")],units=(1,2,3,5))
add("support_resistance","round_numbers(merged price level)",[
 F("cross_round","event","Crossed $1/5/10/50/100","{up,down,none}","",1),
 F("magnet","interaction","≥3 closes within 1% of a round level","{yes,no}",""),
 F("bucket_route","zone_transition","Price bucket start->end","{<1,1-5,5-20,20-100,>100} pairs",""),
 F("sub_dollar_share","persistence","Share of window <$1","{all,some,none}",""),
 F("approach_route","stretch","Toward/away from next round level","{approaching,leaving}",""),
 F("rejection","sequence","Touched round level then reversed","{yes,no}","")])
add("return_path","daily_returns",[
 F("efficiency","shape","Chop ratio = path length / |net change| (inverse Kaufman ER; merged case_chart4)","{smooth<2,mid,choppy>5}","sum|ΔC|/|C[-1]-C[0]|"),
 F("speed","acceleration","Return last third vs first third","{speeding,slowing,steady}",""),
 F("skew","balance","Skew","{pos,neg,neutral}",""),
 F("autocorr","structure","Lag-1 autocorr","{trending,mean_reverting,none}",""),
 F("route","sequence","Up-then-down vs down-then-up","{up_down,down_up,straight_up,straight_down,flat}",""),
 F("tail_event","event","Any |ret|>3σ","{up,down,none}","",1),
 F("down_vs_up","asymmetry","Down moves bigger than up moves","{downs_bigger,ups_bigger,equal}","",1),
 F("staircase_shelves","shelf_structure","Staircase: flat shelves in the trend (≥3 bars, range ≤1 ATR), their count, mean length and whether each shelf sits above the last","{rising_shelves_2+,falling_shelves_2+,mixed,none}x{short<5,long>=5 bars}","shelves from bars < D; compare successive shelf midpoints"),
 F("segment_compare","segment_compare","Slope of the rally segment vs the decline segment (split at window low)","{rally_steeper,decline_steeper,similar}","|slope| ratio 1.25")])
add("liquidity_float","float_turnover",[
 F("turnover_trend","directional","Volume/float slope","{rising,falling,flat}","float from filings published < D"),
 F("float_change","event","Float/shares out changed (offering, split)","{up,down,none}",""),
 F("turnover_vs_past","character","Turnover vs own past","{high,normal,low}",""),
 F("spread_proxy_route","zone_transition","High-low spread proxy tercile start->end","{tight,mid,wide} pairs","Corwin-Schultz"),
 F("zero_volume_days","persistence","Share of zero/near-zero volume days","{none,some,many}",""),
 F("cumulative_turnover","magnitude","Window turnover as multiple of float","{<0.5x,0.5-2x,>2x}","")],units=(1,2,5))
add("calendar","calendar_context",[
 F("month_turn","event","Window spans month-end","{yes,no}","",1),
 F("opex","timing","Bars since monthly opex","{0-5,6-10,>10}",""),
 F("pre_holiday","event_hol","Window contains pre-holiday session","{yes,no}","",1),
 F("weekday_drift","balance","Up-days concentrated Mon vs Fri","{mon,fri,even}",""),
 F("quarter_pos","location","Position in quarter","{early,mid,late}",""),
 F("seasonal_vs_own","character","Window return vs own same-calendar-window history","{above,below,none}","prior years only")],units=(1,),lbs=(5,10,20),note="calendar is known in advance; still uses no prices >= D")
add("market_condition","SPY_VIX",[
 F("spy_trend","directional","SPY slope","{up,down,flat}",""),
 F("vix_route","zone_transition","VIX zone start->end","{<15,15-25,>25} pairs",""),
 F("vix_spike","event","VIX +30% in ≤5 bars","{yes,no}",""),
 F("breadth","balance","Share of universe above SMA50 trend","{rising,falling,flat}","universe as of D-1"),
 F("stock_vs_regime","divergence","Stock trend vs SPY trend","{with,against}",""),
 F("speed","acceleration","SPY move last third vs first","{speeding,slowing,steady}","")])
add("setup_score","checklist_score_path",[
 F("score_trend","directional","Daily setup score (count of bullish checklist answers) slope","{rising,falling,flat}","score(d) built only from bars < d"),
 F("score_price_divergence","divergence","Score rises while price flat/down (Cyrus divergence)","{bull_div,bear_div,none}","score slope>0 & |price ret|<1 ATR or <0"),
 F("score_flip","crossover","Score crossed its 50% line","{up,down,none}",""),
 F("score_speed","acceleration","Score change last third vs first","{speeding,slowing,steady}",""),
 F("score_route","zone_transition","Score tercile start->end","{low,mid,high} pairs",""),
 F("score_vs_own_past","character","Score vs own history","{high,normal,low}",""),
 F("pattern_repeat","repeat","Same stock showed this pattern earlier, and its prior outcome (outcome window must end before D)","{seen_prior_up,seen_prior_down,seen_mixed,not_seen}","lookalike only if outcome window crosses D - not allowed")],lbs=(5,10,20,60),note="second-order: depends on frozen checklist definition")
EV=[("earnings",[F("gap_reaction","event","Earnings day inside the leg and its gap direction (merged #8)","{in_up_leg,in_down_leg}x{gap_up,gap_down}+none","keyed by publication date"),F("beat_miss","directional","EPS vs consensus","{beat,miss,inline}",""),F("drift_after","sequence","Price drift after report vs gap","{continued,faded,none}",""),F("streak","run","Consecutive beats","{0,1,2+}",""),F("time_since","timing","Bars since report","{<5,5-20,>20}",""),F("pre_run","asymmetry","Run-up into report","{up,down,flat}","")],"published: report timestamp (pre/after market)"),
 ("form4",[F("insider_count","run","Distinct insiders","{0,1,2+}",""),F("buy_vs_sell","directional","Net buy/sell","{buy,sell,mixed}",""),F("near_extreme","extreme_timing","Insider buy at/near the window low (mirror: sell near the high)","{buy_near_low,sell_near_high,none}","within 5 bars of strict pivot; Form 4 filing date"),F("cluster","structure","≥2 insiders within 5 bars","{yes,no}",""),F("officer_type","category","Role of largest trade","{ceo_cfo,director,10pct,none}",""),F("price_after","sequence","Price after filing","{up,down,flat}",""),F("time_since","timing","Bars since latest filing","{<5,5-20,>20,none}","")],"published: Form 4 filing date (≤2 business days after trade); never trade date"),
 ("short_interest",[F("si_trend","directional","SI % float change across reports","{up,down,flat}",""),F("dtc_route","zone_transition","Days-to-cover bucket start->end","{<2,2-5,>5} pairs",""),F("si_vs_price","divergence","SI vs price: building during the fall vs during the rise (merged #8)","{si_up_price_down(building_in_fall),si_up_price_up(squeeze_fuel),si_down_price_up,si_down_price_down,none}",""),F("si_vs_own_past","character","SI vs own history","{high,normal,low}",""),F("report_count_rising","run","Consecutive rising reports","{0,1,2+}",""),F("level_bucket","magnitude","Change size","{>20%,5-20%,<5%}","")],"published: FINRA publication ≈8 business days after settlement date; key on publication"),
 ("halts",[F("halt_occurred","event","Halt in window","{yes,no}",""),F("halt_type","category","Reason","{LUDP,news,regulatory}",""),F("halt_count","run","Count","{0,1,2+}",""),F("direction_before","directional","Move into halt","{up,down}",""),F("resume_reaction","sequence","Resume gap","{up,down,flat}",""),F("time_since","timing","Bars since","{<5,5-20,>20,none}","")],"published: halt timestamp < D"),
 ("reg_sho",[F("days_on_list","run","Days on threshold list in window","{0,1-5,>5}",""),F("on_off_route","zone_transition","Status start->end","{on,off} pairs",""),F("entered","event","Added in window","{yes,no}",""),F("exited","event_exit","Removed in window","{yes,no}",""),F("price_while_on","directional","Price trend while listed","{up,down,flat}",""),F("repeat","character","Listed before in prior 250 bars","{yes,no}","")],"published: list date < D; 2020-24 list already built: sha d5032717..., Drive 1HYHBYJN59Sk7sw9mKw6zaahMP9g-XJ87")]
EV.append(("analyst_actions",[F("net_direction","directional","Upgrades vs downgrades on the route","{net_up,net_down,mixed,none}",""),F("count","run","Actions in window","{0,1,2+}",""),F("in_leg","extreme_timing","Action inside up leg vs down leg","{in_up_leg,in_down_leg,none}",""),F("price_after","sequence","Price after action","{continued,reversed,flat}",""),F("cluster","structure","≥2 actions within 5 bars","{yes,no}",""),F("time_since","timing","Bars since last action","{<5,5-20,>20,none}","")],"keyed by publication date; dated source for 2020-24 not yet located on box"))
for v,fs,n in EV: add("events",v,fs,units=(1,),lbs=(10,20,60,120),note=n)

# ---------- draft 2.6 additions (round 3 reads); all sizes in ATR14 units measured < D ----------
def _app(t,v,f):
  for vv in T[t]:
    if vv[0]==v: vv[1].append(f); return
  raise KeyError((t,v))
R3=[
("extremes","base_and_run",F("pause_vs_run","pause_run_ratio","Bars in the current flat stretch (range <=3 ATR) / bars in the leg before it; bull = pause after up leg, bear = pause after down leg","{after_up,after_down}x{short<0.33,mid,long>1}","len(flat)/len(prior leg); leg per 3-ATR rule")),
("extremes","new_highs_lows",F("low_spacing","swing_rhythm","Bars between successive strict swing lows (bull) / swing highs (bear), regular vs uneven","{lows,highs}x{regular(cv<0.25),uneven,<3 pivots}","coefficient of variation of pivot gaps")),
("volume","RVOL20",F("absorption_day","absorption","Day with RVOL>3 but |C/Cprev-1| < 0.5 ATR%; bull = at/after a decline, bear = at/after a rise; age in bars","{after_decline,after_rise,none}x{age<=5,6-20,>20}","")),
("extremes","new_highs_lows",F("giveback_speed","giveback_speed","Bars to give back half of the last leg / bars the leg took (bull: down leg recovered; bear: up leg given back)","{fast<0.5,similar,slow>2}x{bull,bear}","3-ATR legs")),
("overbought_oversold","RSI6",F("osc_swing_speed","osc_swing_speed","Bars from RSI6 >=80 to <=20 (bear) or <=20 to >=80 (bull), latest such swing","{bull,bear}x{<=5,6-15,>15,none}","")),
("volume","RVOL20",F("ledge_fade","ledge_fade","Volume slope across the current flat stretch (range <=3 ATR, >=5 bars) relative to the leg before it; after up leg = bull ledge, after down leg = bear ledge","{after_up,after_down}x{fading<0.7,steady,rising>1.3}","mean vol(ledge)/mean vol(prior leg) and OLS sign")),
("moving_averages","MA_group(10/20/50/200)",F("ma30_side_streak","side_streak","Current run of closes above SMA30 (bull) or below (bear), in bars, vs its own longest run in 500 bars","{above,below}x{<10,10-30,>30}x{record,not}","")),
("support_resistance","prior_pivots",F("fail_fail_break","fail_sequence","Order: >=2 failed pokes above a level (each closing back below within 3 bars) then a close >1 ATR below the base (bear); mirror: >=2 failed breaks below then close >1 ATR above (bull)","{bull,bear,none}","levels per +-0.5 ATR rule")),
("extremes","base_and_run",F("shelf_depth","shelf_depth","Height of the current shelf / height of the leg before it, both in ATR (bull after up leg, bear after down leg)","{after_up,after_down}x{shallow<0.25,mid,deep>0.5}","")),
("range_position","Donchian20",F("fail_shape","fail_shape","Shape of the latest failed break above (bear) or below (bull) the channel: same-day rejection (wick beyond, close inside) vs multi-day hold (>=2 closes beyond) then back inside","{bull,bear}x{same_day,multi_day,none}","")),
("volume","RVOL20",F("maxvol_wick","maxvol_wick","Wicks on the window's max-volume bar in ATR: long lower wick = bull, long upper wick = bear","{bull_wick>1ATR,bear_wick>1ATR,small}","")),
("volume","RVOL20",F("pullback_vs_run_volume","pullback_volume","Mean volume in the pullback after the last up leg / mean volume in that leg (bull setup); mirror: bounce after last down leg vs that leg (bear)","{bull,bear}x{lighter<0.7,similar,heavier>1.3}","split at the window high (mirror of segment_compare, which splits at the low)")),
]
for t,v,f in R3: _app(t,v,f)
PH=[F("phase_count","phase_count","Number of phases in the window (3-ATR leg rule)","{1,2-3,4-6,7+}",""),
 F("last_phase","phase_label","Label of the phase ending at D-1","{up_run,down_run,shock_up,shock_down,base,retest_high,retest_low,break_up,break_down}","fixed rules below"),
 F("phase_seq3","phase_sequence","Labels of the last 3 phases in order","ordered triples of labels",""),
 F("len_vs_prev","phase_length_ratio","Last phase length / previous phase length; bull or bear by last-phase direction","{up,down,flat}x{<0.5,0.5-2,>2}",""),
 F("size_vs_prev","phase_size_ratio","Last phase size in ATR / previous phase size in ATR","{up,down,flat}x{<0.5,0.5-2,>2}",""),
 F("vol_vs_prev","phase_volume_ratio","Last phase mean volume / previous phase mean volume","{up,down,flat}x{<0.7,0.7-1.3,>1.3}",""),
 F("speed_vs_prev","phase_speed_ratio","Last phase ATR per bar / previous phase ATR per bar","{up,down,flat}x{slower,similar,faster}","")]
add("phase_list","3ATR_legs",PH,note="Cut: a leg ends when price reverses >=3 ATR14 from its extreme (zigzag, ATR at leg start); stretches where no 3-ATR move happens over >=10 bars = base. Labels: up_run/down_run = leg >=3 ATR and >=5 bars; shock = leg >=3 ATR in <=3 bars; base = range <=3 ATR for >=10 bars; retest = leg ending within 0.5 ATR of a prior phase extreme; break = close >1 ATR beyond a base range. Per phase store: label, start/end bar, length, size (ATR), mean volume, ratios vs previous phase. Uses bars < D only.")

# ---------- lever 5 ----------
H=["shape","divergence_sync","order_of_events","speed","change_of_state","time_since","route","character_change","retests","squeeze_release","stage","vs_own_past","lead_lag","timeframe_agreement","shock_recovery"]
HK={"divergence_sync":{"divergence"},"speed":{"acceleration","second_order"},"change_of_state":{"zone_transition"},"time_since":{"timing"},"route":{"sequence"},"character_change":{"character"},"retests":{"interaction"},"vs_own_past":{"chain_history","character"},"shape":{"shape"}}
DROP={}
def drop(types,hv,why):
  for t in types: DROP[(t,hv)]=why
ALL=list(T)
drop(["calendar"],"shape","calendar has no curve");drop(["calendar"],"divergence_sync","no paired line");drop(["calendar"],"retests","no levels");drop(["calendar"],"squeeze_release","no volatility");drop(["calendar"],"stage","no trend");drop(["calendar"],"lead_lag","not a price series");drop(["calendar"],"shock_recovery","no shocks");drop(["calendar"],"speed","no magnitude");drop(["calendar"],"timeframe_agreement","calendar is timeframe-free");drop(["calendar"],"route","no path");drop(["calendar"],"order_of_events","only 1 event kind")
drop(["events"],"shape","events are sparse, no curve");drop(["events"],"squeeze_release","no volatility line");drop(["events"],"timeframe_agreement","1-day units only");drop(["events"],"retests","no price levels");drop(["events"],"lead_lag","sparse; can't estimate habit")
drop(["liquidity_float"],"retests","no levels");drop(["liquidity_float"],"stage","stage is a price concept");drop(["liquidity_float"],"lead_lag","float isn't benchmarked")
drop(["market_condition"],"lead_lag","is the benchmark itself");drop(["market_condition"],"retests","SPY levels belong to price types")
drop(["setup_score"],"retests","score has no levels");drop(["setup_score"],"lead_lag","score vs sector score not built");drop(["setup_score"],"timeframe_agreement","score defined on 1d only");drop(["setup_score"],"shape","would be a lookalike input")
drop(["extremes"],"squeeze_release","use volatility type");drop(["return_path"],"retests","returns have no levels")
drop(["candles","support_resistance","extremes","range_position"],"lead_lag","lead/lag lives in relative_strength");drop(["volatility"],"retests","vol has no levels")
LOOK={"shape"}  # lookalike inputs (need future returns of twins)
SRC="current_sector_label (survivors-only, known leak risk)";PF="excludes names failing liquidity + $100M rule as of D-1; no-share-count names kept"
CC={("daily_returns","staircase_shelves"):"case_chart1",("MA_group(10/20/50/200)","deepest_pullback_ma"):"case_chart1",("MA_group(10/20/50/200)","full_bull_streak"):"case_chart1",("RSI14","rsi_floor"):"case_chart1",("RSI12","length_fan"):"case_chart1",
("drawdown","second_leg"):"case_chart2",("RSI14","price_divergence"):"case_chart2(merged: RSI low vs price low at second low)",
("squeeze(BB_in_Keltner)","release_gap"):"case_chart3",("squeeze(BB_in_Keltner)","release_close_location"):"case_chart3",("squeeze(BB_in_Keltner)","release_volume"):"case_chart3(merged)",("new_highs_lows","swing_count"):"case_chart3+case_chart4(merged HL/LH)",
("daily_returns","efficiency"):"case_chart4(merged chop ratio)",
("ATR14","shock"):"GLND(merged spike vs usual)",("new_highs_lows","giveback"):"GLND(extended to spikes)",("base_and_run","vol_vs_base"):"GLND",("base_and_run","round_trip"):"GLND",("base_and_run","base_tightness"):"GLND",("base_and_run","run_length"):"GLND",
("base_and_run","run_multiple"):"James",("base_and_run","first_ma20_touch"):"James",("MA_group(10/20/50/200)","bunching_route"):"James(merged)",
("drawdown","capitulation_bar"):"VSTS+James(mirror)",
("unfilled_gaps","partial_fill"):"cyrus_shots(merged gap-fill progress)",("base_and_run","at_launch_shelf"):"cyrus_shots",
("drawdown","second_low_volume"):"case_chart6",("MA_group(10/20/50/200)","full_stack_streak"):"case_chart1+case_chart5(merged bear days)",("MA_group(10/20/50/200)","bounce_ceiling"):"case_chart5",
("unfilled_gaps","leg_start_gap"):"case_chart5",("unfilled_gaps","first_bounce_winback"):"case_chart5",
("drawdown","climax_context"):"grok",("base_and_run","peak_volume"):"grok",("RSI14","rsi_ceiling"):"James(mirror)",("RVOL20","dry_up_at_low"):"James(mirror)"}
for _v in ("vs_SPY","vs_sector_peers","vs_theme_peers"):
  CC[(_v,"leg_attribution")]="newbot/theme_radar/james/manager"; CC[(_v,"own_vs_bench_days")]="newbot/theme_radar/james/manager"; CC[(_v,"turn_sync")]="why_who#2"
CC.update({("up_down_volume","trend"):"why_who#3(merged; overlaps OBV/AD)",("OHLC","close_location_route"):"why_who#4",("OHLC","wick_evolution"):"why_who#5",
("volume_profile","overhead_supply"):"why_who#6(volume-at-price)",("volume_profile","holder_cost"):"why_who#6(volume-at-price)",("unfilled_gaps","gap_count"):"why_who#7(merged)",
("earnings","gap_reaction"):"why_who#8(merged)",("form4","near_extreme"):"why_who#8",("short_interest","si_vs_price"):"why_who#8(merged)",("reg_sho","days_on_list"):"why_who#8(already present)",
("OHLC","overnight_vs_intraday"):"why_who#9+taskforce_BE_TER(merged)",("prior_pivots","current_level_touches"):"why_who#10(merged)",("ATR14","range_calming"):"why_who#11+taskforce_BE_TER",
("big_picture","multi_year_position"):"why_who#12+taskforce_BE_TER(2y)",("checklist_score_path","pattern_repeat"):"why_who#13",
("drawdown","move_duration"):"taskforce_BE_TER",("drawdown","climax_context"):"grok+taskforce_BE_TER(merged shock vs worn-out)",
("drawdown","capitulation_bar"):"VSTS+James(mirror)+case_chart9(merged record-vol close/wick)",("base_and_run","parabolic_reversal_day"):"case_chart7",("base_and_run","rehearsal"):"case_chart7",
("MA_group(10/20/50/200)","bunching_route"):"James+case_chart7(merged stretch vs own history)",("new_highs_lows","hl_base_breakout"):"case_chart10"})
for _f in ("net_direction","count","in_leg","price_after","cluster","time_since"): CC[("analyst_actions",_f)]="why_who#8"
for _f in ("weekly_trend","dist_from_high","ath_age","weekly_stack","range_route"): CC[("big_picture",_f)]="why_who#12"
CC[("RSI14","price_divergence")]="case_chart2+case_chart6(merged: RSI higher at second low)"
for _n in ("RSI6","RSI12","RSI24"):
  for _f in ("rsi_floor","rsi_ceiling","price_divergence"): CC[(_n,_f)]=CC[("RSI14",_f)]
CC[("new_highs_lows","giveback")]="GLND+grok(extended to spikes and whole run)"
CC[("drawdown","second_leg")]="case_chart2+James(mirror)"
for _m in ("SMA20","SMA50","SMA200","EMA21"): CC[(_m,"cross_count")]="case_chart4"; CC[(_m,"touch_order")]="cyrus_shots"
rows=[];base=collections.Counter();fam=collections.Counter();hrows=[];checks=[]
for t,vs in T.items():
  for v,fs,us,lbs,note,opt in vs:
    kinds=[f[1] for f in fs];ok6="yes" if len(fs)>=6 and len(set(kinds))==len(kinds) else "NO"
    checks.append((t,v,len(fs),ok6))
    for f in fs:
      short=f[5] if len(f)>5 else 0
      tf=[(u,b) for u in us for b in lbs if not tfok(u,b,short)]
      sec=("sector" in v)
      rows.append([t,v,f[0],f[1],f[2],f[3],f[4],"|".join(map(str,sorted({u for u,_ in tf}))),"|".join(f"{u}x{b}" for u,b in tf),LEAK,"; ".join(x for x in(note,opt) if x),ok6,"yes",SRC if sec else "",PF if sec else "",CC.get((v,f[0]),"")])
      base[t]+=len(tf)
    tf10=[(u,b) for u in us for b in lbs if not tfok(u,b,0)]
    for h in H:
      why=DROP.get((t,h))
      if not why and HK.get(h,set())&set(kinds): why="duplicate of existing facet kind "+",".join(HK[h]&set(kinds))
      st="drop" if why else ("lookalike_input" if h in LOOK else "keep")
      hrows.append([t,v,h,st,why or ("needs twins' future returns -> lookalike input, not a yes/no question" if h in LOOK else ""),len(tf10) if st=="keep" else 0])
      if st=="keep": fam[t]+=len(tf10)
H5="lever1_type variant facet facet_kind definition answer_set formula valid_units valid_lookbacks leak_rule notes facet_count_ok snapshot_free sector_source peer_filter source".split()
with open("DIAL_TABLE.csv","w",newline="") as fh: w=csv.writer(fh,lineterminator="\n");w.writerow(H5);w.writerows(rows)
with open("HISTORY_LEVER.csv","w",newline="") as fh: w=csv.writer(fh,lineterminator="\n");w.writerow(["lever1_type","variant","history_value","status","reason","question_families"]);w.writerows(hrows)
import json;json.dump({"rows":len(rows),"base":dict(base),"base_total":sum(base.values()),"fam":dict(fam),"fam_total":sum(fam.values()),"checks_fail":[c for c in checks if c[3]!="yes"],"nvariants":len(checks),"invalid":[(u,b,tfok(u,b,0)) for u in U for b in B if tfok(u,b,0)],"hstatus":dict(collections.Counter(r[3] for r in hrows))},open("counts.json","w"),indent=0)
