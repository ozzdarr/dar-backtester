
#from queries import *
#from ib_bars import convert_bars_size
from csv_templates import *

def current_bot_strategy(hint, bars, options, bars_service):
    return defensive_strategy(hint, bars, options, bars_service)

def defensive_strategy(hint, bars, options, bars_service):
    exit_bar = None
    entry_trigger = hint.entryTrigger
    target = hint.defaultTarget
    defend = hint.defaultDefend

    entry_bar, error_processed_hint = hint.entryQuery(bars,entry_trigger)
    if error_processed_hint:
        return error_processed_hint

    for bar in bars:
        #if bar.date >= options['defensive_change_scale_time']:
            #bars_5m =
        defend = bar.isDefensivePattern(bars,defend)
        if bar.isDefendReach(defend):
            exit_bar, exit_price = bar.isDefendReach
            processed_hint = processed_hint_template(hint,options,entry_bar,entry_trigger,exit_bar,exit_price)
            return  processed_hint
    if not exit_bar:
        processed_hint = processed_hint_template(hint, options, entry_bar, entry_trigger)
        return processed_hint

def one_to_one(hint, bars, options):
    #Todo:  round numbers
    exit_bar = None
    entry_trigger = hint.userEntryTrigger(options)
    target = hint.defaultTarget(options)

    if hint.hasNoDefend or hint.hasBigUserDefend(options) or hint.hasUnreasonableUserDefend(options):
        defend = hint.defaultDefend
    else:
        defend = hint.userDefend(options)

    entry_bar = hint.entryQuery(bars, entry_trigger, options)
    if not entry_bar:
        did_not_enter_hint = processed_hint_template(hint,options)
        return did_not_enter_hint
    if type(entry_bar) is str:
        return processed_hint_template(hint, options, error=entry_bar)

    # Prepare bars to keep only the valid ones.
    bars = bars[:-options['kill_trade_time']]

    bars = list(filter(lambda x: x.date >= entry_bar.date.replace(second=0), bars))



    for bar in bars:
        # Exit check
        if bar.isDefendReach(hint,defend) and bar.isTargetReach(hint,target):
            if bar.isDefendReach.date(hint,defend) < bar.isTargetReach(hint,target).date:
                exit_bar, exit_price = bar.isDefendReach(hint,defend)
            else:
                exit_bar, exit_price = bar.isTargetReach(hint,target)

        elif bar.isDefendReach(hint,defend):
            exit_bar, exit_price = bar.isDefendReach(hint,defend)

        elif bar.isTargetReach(hint,target):
            exit_bar, exit_price = bar.isTargetReach(hint,target)

        if exit_bar:
            processed_hint = processed_hint_template(hint,options,entry_bar,entry_trigger,exit_bar,exit_price)
            return processed_hint

    # Kill trade before end of day
    if not exit_bar:
        processed_hint = processed_hint_template(hint, options, entry_bar, entry_trigger, bars=bars)
        return processed_hint
