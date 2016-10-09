
from queries import *
from ib_bars import convert_bars_size
from csv_templates import *

def current_bot_strategy(hint, bars, options, bars_service):
    return defensive_strategy(hint, bars, options, bars_service)

def defensive_strategy(hint, bars, options, bars_service):
    entry_trigger = hint.entryTrigger
    target = hint.defaultTarget
    defend = hint.defaultDefend

    entry_bar, error_processed_hint = hint.entryQuery(bars,entry_trigger)
    if error_processed_hint:
        return error_processed_hint

    for bar in bars:
        defend = bar.isDefensivePattern(bars,defend)
        if bar.isDefendReach(defend):
            exit_bar, exit_price = bar.isDefendReach
            processed_hint = processed_hint_template(hint,options,entry_bar,entry_trigger,exit_bar,exit_price)
            return  processed_hint
    if not exit_bar:
        processed_hint = processed_hint_template(hint, options, entry_bar, entry_trigger)
        return processed_hint

def one_to_one(hint, bars, options):
    entry_trigger = hint.entryTrigger(options)
    target = hint.defaultTarget
    defend = hint.defaultDefend

    entry_bar = hint.entryQuery(bars, entry_trigger, options)
    if not entry_bar:
        did_not_enter_hint = processed_hint_template(hint,options)
        return did_not_enter_hint
    if type(entry_bar) is str:
        return processed_hint_template(hint, options, error=entry_bar)

    # Prepare bars to keep only the valid ones.
    bars = bars[:-options['kill_trade_time']]
    bars = list(filter(lambda x: x.date >= entry_bar.date, bars))

    for bar in bars:
        # Exit check
        if bar.isDefendReach(entry_bar,defend) and bar.isTargetReach(entry_bar,target):
            if bar.isDefendReach.date < bar.isTargetReach.date:
                exit_bar, exit_price = bar.isDefendReach(defend)
            else:
                exit_bar, exit_price = bar.isTargetReach(target)

        elif bar.isDefendReach:
            exit_bar, exit_price = bar.isDefendReach(defend)

        elif bar.isTargetReach:
            exit_bar, exit_price = bar.isTargetReach(target)

        if exit_bar:
            processed_hint = processed_hint_template(hint,options,entry_bar,entry_trigger,exit_bar,exit_price)
            return processed_hint

    # Kill trade before end of day
    if not exit_bar:
        processed_hint = processed_hint_template(hint, options, entry_bar, entry_trigger)
        return processed_hint
