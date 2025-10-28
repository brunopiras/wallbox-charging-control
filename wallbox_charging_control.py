"""
'Python_Script Home Assistant per gestione Wallbox con impianto fotovoltaico e batteria senza immissione di corrente in rete.'
'Autore: [bruno[AT]casapiras.it]'
'Wallbox Dynamic Controller v2025.10.12'
Funzionalità Script:
    Lo script utilizza diverse entità di Home Assistant (template o di sistema/integrazioni) per monitorare lo stato della Wallbox.
    Allo stesso tempo riesce a veicolare sulla Wallbox la giusta quantita di corrente tenendo sotto controllo il consummo massimo della casa, 
    la ricarica della batteria FTV e altri valori.
    Viene avviato (dopo essere stato copiato nella cartella /config/python_script) tramite una automazione di Home Assistant ogni X secondi(45 nel mio caso).
Modifiche 27/10/2025:
- FIX: Ripristinato lo stato 'Non Collegato' quando la wallbox è in idle, come nel comportamento originale.
- HOTFIX: Corretto un errore di battitura (typo) che causava il crash dello script.
- REFACTORING: Suddivisione della logica in funzioni per migliore leggibilità e manutenibilità.
"""

# === 1. CONFIGURAZIONE CENTRALE ===
CONFIG = {
    "entities": {
        "debug_mode": "input_boolean.wboxdebug",                                    #<-Helper per attivare o disattivare il DEBUG<>#
        "voltage": "sensor.silla_prism_power_grid_voltage",                         #<-Sensore Tensione Rete<>#
        "wallbox_state": "sensor.silla_prism_current_state",                        #<-Sensore stato wallbox<>#
        "current_timestamp": "sensor.current_timestamp",                            #<-Sensore Template timestamp<>#
        "wallbox_set_mode": "select.silla_prism_set_mode",                          #<-Select modo Wallbox<>#
        "wallbox_set_current": "number.silla_prism_set_max_current",                #<-Number per regolare la corrente di carica Wallbox<>#
        "last_tag_time": "input_datetime.last_wbox_tag",                            #<-Input per memorizzare Uso Tag Rfid<>#   
        "pv_primary_1": "sensor.deyeha_pv1_power",                                  #<-Sensore Potenza Deye Stringa FTV 1<># 
        "pv_primary_2": "sensor.deyeha_pv2_power",                                  #<-Sensore Potenza Deye Stringa FTV 2<>#  
        "pv_secondary": "sensor.inverter_lcd_pv_power",                             #<-Sensore Potenza Genius Stringa FTV<>#
        "pv_total": "sensor.deye_pv_power",                                         #<-Sensore Template PW Totale Impianto FTV<>#  
        "pv_losses": "sensor.deyeha_power_losses",                                  #<-Sensore Perdite PW Deye<>#  
        "batt_power": "sensor.tdt_bms_power_inverted",                              #<-Sensore Template Invertito (Scarica'+'/Carica'-') PW BMS<>#   
        "batt_max_discharge": "input_number.battmaxdischarge",                      #<-Number Potenza Massima cedibile dall Batteria<>#  
        "batt_soc": "sensor.deyeha_battery",                                        #<-Sensore Deye % SOC Batteria<>#          
        "batt_soc_min": "input_number.wboxsocmin",                                  #<-Number SOC Minimo Batteria per Logica Ricarica<>#
        "batt_soc_priority": "input_number.wboxsocchargepriority",                  #<-Number SOC Intervallo tra minimo e questo in cui applichi Logica Divisione PW Ricarica<>#                
        "batt_protection_cycles": "input_number.wallbox_batt_protection_cycles",    #<-Number Numero di cicli in cui si evita la logica di Ricarica<>#
        "min_charge_amps": "input_number.wboxminamp",                               #<-Number Corrente minima di ricarica Wallbox (minore non accetta)<># 
        "max_charge_amps": "input_number.wboxmaxamp",                               #<-Number Corrente massima di ricarica Wallbox (superiore non accetta)<># 
        "force_charge": "input_boolean.wboxforzacharge",                            #<-Helper per evitare i controlli bloccanti (USARE CON CAUTELA!!)<>#  
        "home_power": "sensor.green_power",                                         #<-Sensore Zigbee PW assorbita dalla casa (comprende ovviamente anche la Wallbox)<># 
        "home_current": "sensor.green_current",                                     #<-Sensore Zigbee Corrente assorbita dalla casa (comprende ovviamente anche la Wallbox)<># 
        "home_max_current": "input_number.wboxmaxhomecurrent",                      #<-Number Corrente massima che l\'impianto di casa puo' assorbire (comprende ovviamente anche la Wallbox)<># 
        "wallbox_power": "sensor.silla_prism_output_power",                         #<-Sensore Wallbox PW erogata<>#  
        "ev_soc": "sensor.ev3_ev_battery_level",                                    #<-Sensore Kia SOC Auto (si aggiorna circa ogni 15min)<>#
        "ev_target_soc": "input_number.ev_target_soc",                              #<-Number Target di ricarica Batteria Kia<>#      
        "time": "sensor.time",                                                      #<-Sensore Tempo<>#    
        "pause_start_time": "input_datetime.wbox_orainizio",                        #<-Input Ora e minuti Inizio Pausa Ricarica<>#    
        "pause_end_time": "input_datetime.wbox_orafine",                            #<-Input Ora e minuti Fine Pausa Ricarica<>#      
        "sun": "sun.sun",                                                           #<-Sensore Sole<>#
        "sun_elevation_threshold": "input_number.wboxelevation",                    #<-Number Elevazione del Sole sotto il quale la logica di ricarica non poarte<>#
        "battery_priority_ratio": "input_number.wbox_battery_priority_ratio",       #<-Number Percentuale di divisione della ricarica tra macchina e batteria casa (quando necessario)<>#    
        "last_wallbox_current": "input_number.last_wallbox_current",                #<-Number Ultima Corrente impostata dallo script<>#
        "date_time_iso": "sensor.date_time_iso",                                    #<-Sensore Template data e ora<>#
        "current_timestamp": "sensor.current_timestamp",                            #<-Sensore Template timestamp Unix<>#
        "last_wbox_tag": "input_datetime.last_wbox_tag",                            #<-Input Ultimo utilizzo TAG Rfid<>#
        "status_sensor": "sensor.wallbox_status"                                    #<-Sensor Template creato e aggiornato dallo Script<>#  
    },
    "params": {
        "post_tag_lock_seconds": 180,                                               #<-Tempo di blocco dopo l\'RFID (Scenario 2)<>#
        "stabilization_delta_amp": 1.0,                                             #<-Delta minimo di corrente per l\'aggiornamento (Scenario 14)<>#    
        "min_power_ratio_for_min_amps": 0.6,                                        #<-Percentuale di potenza per forzare i min_amp (0.6 = 60%)<>#
        "min_secondary_inverter_power": 100,                                        #<-Soglia per considerare attivo l\'inverter secondario<>#
        "batt_discharge_margin": 0.8,                                               #<-Ulteriore margine di sicurezza di scarica batteria 80% del massimo consentito<>#    
        "force_charge_soc_threshold": 95.0,                                         #<-Oltre 95% SOC, forza la carica massima<>#
        "pv_safety_margin_ratio": 0.1,                                              #<-10% di margine sull\'eccedenza<>#
        "batt_protection_cycles_on_fault": 3                                        #<-Numero di cicli in cui si evita la logica di Ricarica<>#    
    }
}

# === 2. FUNZIONI HELPER ===

def log_debug(message):
    if DEBUG_MODE:
        logger.info(message)

def log_always(message):
    logger.info(message)

def get_str(entity_id, default='unavailable'):
    state = hass.states.get(entity_id)
    if state is None:
        log_debug(f"[Wallbox] Entità {entity_id} non trovata. Ritorno default '{default}'.")
        return default
    return state.state

def get_float(entity_id, default=0.0, decimals=3):
    state_obj = hass.states.get(entity_id)
    if state_obj is None:
        log_debug(f"[Wallbox] Entità {entity_id} non trovata. Ritorno default {default}.")
        return default
    try:
        return round(float(state_obj.state), decimals)
    except (TypeError, ValueError):
        log_debug(f"[Wallbox] Valore non numerico per {entity_id}: {state_obj.state} -> uso default {default}")
        return default

def get_float_attr(entity_id, attribute, default=0.0, decimals=3):
    state_obj = hass.states.get(entity_id)
    if state_obj is None:
        log_debug(f"[Wallbox] Entità {entity_id} non trovata per l\'attributo '{attribute}'. Ritorno default {default}.")
        return default
    val = state_obj.attributes.get(attribute)
    try:
        return round(float(val), decimals)
    except (TypeError, ValueError):
        log_debug(f"[Wallbox] Attributo non numerico per {entity_id}.{attribute}: {val} -> uso default {default}")
        return default

def get_attr(entity_id, attribute, default=None):
    state_obj = hass.states.get(entity_id)
    if state_obj is None:
        log_debug(f"[Wallbox] Entità {entity_id} non trovata per l\'attributo '{attribute}'. Ritorno default.")
        return default
    return state_obj.attributes.get(attribute, default)

def call_service(domain, service, service_data, log_error=True):
    try:
        hass.services.call(domain, service, service_data, blocking=True)
        return True
    except Exception as e:
        if log_error:
            log_always(f"[Wallbox] Errore chiamata servizio {domain}.{service}: {e}")
        return False

def time_diff_seconds_approx(full_now, full_past):
    try:
        y1, mo1, d1 = [int(x) for x in full_now[:10].split("-")]
        h1, mi1, s1 = [int(x) for x in full_now[11:19].split(":")]
        y2, mo2, d2 = [int(x) for x in full_past[:10].split("-")]
        h2, mi2, s2 = [int(x) for x in full_past[11:19].split(":")]
        days1 = y1 * 365 + mo1 * 30 + d1
        days2 = y2 * 365 + mo2 * 30 + d2
        total1 = days1 * 86400 + h1 * 3600 + mi1 * 60 + s1
        total2 = days2 * 86400 + h2 * 3600 + mi2 * 60 + s2
        return total1 - total2
    except:
        return 0

# === 3. LOGICA DELLO SCRIPT ===

def get_system_state(cfg):
    state = {}
    entities = cfg["entities"]
    state["voltage"] = get_float(entities["voltage"])
    state["forzacharge"] = get_str(entities["force_charge"]) == "on"
    pv_primary = get_float(entities["pv_primary_1"]) + get_float(entities["pv_primary_2"])
    pv_secondary = get_float(entities["pv_secondary"])
    state["inverter_secondary_active"] = pv_secondary > cfg["params"]["min_secondary_inverter_power"]
    pv_lordo = get_float(entities["pv_total"]) if state["inverter_secondary_active"] else pv_primary
    state["pv_power"] = pv_lordo - get_float(entities["pv_losses"])
    state["pv_primary"] = pv_primary
    state["pv_secondary"] = pv_secondary
    state["batt_power"] = get_float(entities["batt_power"])
    state["batt_max_discharge"] = get_float(entities["batt_max_discharge"])
    state["soc_attuale"] = get_float(entities["batt_soc"])
    state["soc_min"] = get_float(entities["batt_soc_min"])
    state["soc_priority"] = get_float(entities["soc_priority"])
    home_power = get_float(entities["home_power"])
    wallbox_power = get_float(entities["wallbox_power"], 0)
    home_domestic_power = max(0, home_power - wallbox_power)
    state["home_power"] = home_power
    state["home_current"] = get_float(entities["home_current"])
    state["home_max_current"] = get_float(entities["home_max_current"])
    state["pv_excess"] = state["pv_power"] - home_domestic_power
    state["ev_soc"] = get_float(entities["ev_soc"])
    state["ev_target"] = get_float(entities["ev_target_soc"])
    state["ora_attuale"] = get_str(entities["time"])
    state["ora_inizio_pausa"] = get_str(entities["pause_start_time"], "00:00:00")[:5]
    state["ora_fine_pausa"] = get_str(entities["pause_end_time"], "00:00:00")[:5]
    state["sun_elevation"] = get_float_attr(entities["sun"], "elevation")
    state["is_rising"] = get_attr(entities["sun"], "rising", False)
    state["elevation_limit"] = get_float(entities["sun_elevation_threshold"])
    state["min_amp"] = get_float(entities["min_charge_amps"])
    state["max_amp"] = get_float(entities["max_charge_amps"])
    state["min_wallbox_power"] = state["min_amp"] * state["voltage"]
    state["batt_priority_ratio"] = get_float(entities["battery_priority_ratio"])
    return state

def determine_pause_reason(state, cfg):
    entities = cfg["entities"]
    params = cfg["params"]
    if state["forzacharge"]:
        return None
    if state["ev_soc"] >= state["ev_target"]:
        return f"EV SOC target raggiunto ({state['ev_soc']:.1f}%)"
    if state["batt_power"] > state["batt_max_discharge"]:
        call_service("input_number", "set_value", {"entity_id": entities["batt_protection_cycles"], "value": params["batt_protection_cycles_on_fault"]})
        return f"Scarica batteria eccessiva: {state['batt_power']:.0f}W > {state['batt_max_discharge']:.0f}W"
    if state["home_current"] > state["home_max_current"]:
        return f"Consumo casa eccessivo: {state['home_current']:.1f}A > {state['home_max_current']:.1f}A"
    ora_inizio, ora_fine, ora_attuale = state["ora_inizio_pausa"], state["ora_fine_pausa"], state["ora_attuale"]
    if (ora_inizio < ora_fine and ora_inizio <= ora_attuale <= ora_fine) or \
       (ora_inizio > ora_fine and (ora_attuale >= ora_inizio or ora_attuale <= ora_fine)):
        return f"Finestra di pausa attiva ({ora_inizio}-{ora_fine})"
    if state["soc_attuale"] < state["soc_min"]:
        return f"SOC batteria critico: {state['soc_attuale']:.1f}% < {state['soc_min']:.1f}%"
    batt_protection_cycles = get_float(entities["batt_protection_cycles"], 0)
    if batt_protection_cycles > 0:
        new_cycles = max(0, batt_protection_cycles - 1)
        call_service("input_number", "set_value", {"entity_id": entities["batt_protection_cycles"], "value": new_cycles})
        return f"Protezione batteria attiva ({int(batt_protection_cycles)} cicli rimanenti)"
    return None

def calculate_target_amps(state, cfg):
    params = cfg["params"]
    available_power = 0
    pause_reason = None
    if state["sun_elevation"] < state["elevation_limit"] and not state["is_rising"]:
        pause_reason = f"Sole basso in discesa ({state['sun_elevation']:.1f}°)"
    elif not state["forzacharge"] and state["batt_power"] > (state["batt_max_discharge"] * params["batt_discharge_margin"]):
        pause_reason = f"Priorità stop scarica batteria ({state['batt_power']:.0f}W)"
    else:
        if state["soc_attuale"] < state["soc_min"]:
            available_power = 0
        elif state["soc_min"] <= state["soc_attuale"] < state["soc_priority"]:
            if state["pv_excess"] >= state["min_wallbox_power"]:
                excess_after_min = state["pv_excess"] - state["min_wallbox_power"]
                excess_for_batt = excess_after_min * (state["batt_priority_ratio"] / 100.0)
                available_power = state["min_wallbox_power"] + (excess_after_min - excess_for_batt)
            else:
                available_power = 0
        else:
            if state["soc_attuale"] > params["force_charge_soc_threshold"]:
                available_power = state["max_amp"] * state["voltage"]
                log_always(f"[Wallbox] 🚀 MAX CHARGE FORZATA (SOC {state['soc_attuale']:.1f}%): Wallbox a {state['max_amp']:.0f}A.")
            elif state["pv_excess"] >= state["min_wallbox_power"]:
                safety_margin = state["pv_excess"] * params["pv_safety_margin_ratio"]
                available_power = state["pv_excess"] - safety_margin
            else:
                available_power = 0
    clamped_amp = 0
    if available_power > 0:
        available_amp = available_power / state["voltage"]
        if available_amp >= state["min_amp"]:
            clamped_amp = int(round(max(state["min_amp"], min(state["max_amp"], available_amp))))
        elif available_power >= (state["min_wallbox_power"] * params["min_power_ratio_for_min_amps"]):
            clamped_amp = int(state["min_amp"])
    if clamped_amp < state["min_amp"]:
        clamped_amp = 0
        if not pause_reason:
             pause_reason = "Corrente calcolata troppo bassa"
    return clamped_amp, pause_reason

def apply_wallbox_state(target_amps, pause_reason, last_amp, cfg):
    entities = cfg["entities"]
    params = cfg["params"]
    if pause_reason:
        log_debug(f"[Wallbox] Ricarica in pausa: {pause_reason}")
        call_service("select", "select_option", {"entity_id": entities["wallbox_set_mode"], "option": "paused"})
        return 0, True, pause_reason
    final_amps = target_amps
    if target_amps > 0 and last_amp > 0:
        delta = abs(target_amps - last_amp)
        if delta < params["stabilization_delta_amp"]:
            final_amps = last_amp
    log_debug(f"[Wallbox] Corrente impostata a {final_amps}A")
    call_service("number", "set_value", {"entity_id": entities["wallbox_set_current"], "value": final_amps})
    call_service("input_number", "set_value", {"entity_id": entities["last_wallbox_current"], "value": final_amps})
    call_service("select", "select_option", {"entity_id": entities["wallbox_set_mode"], "option": "normal"})
    return final_amps, False, "Carica attiva"

# === 4. ESECUZIONE PRINCIPALE ===

DEBUG_MODE = get_str(CONFIG["entities"]["debug_mode"]) == "on"
script_start_iso = get_str(CONFIG["entities"]["date_time_iso"])
log_always(f"[Wallbox] Script AVVIATO v2025.10.12 - Debug: {'ATTIVO' if DEBUG_MODE else 'DISATTIVO'}")

final_amps, pause_mode, pause_reason, state_data = 0, True, "", {}

if get_str(CONFIG["entities"]["wallbox_state"]) == "idle":
    pause_reason = "Connettore non collegato"
else:
    last_tag_timestamp = get_float_attr(CONFIG["entities"]["last_tag_time"], "timestamp", 0)
    now_timestamp = get_float(CONFIG["entities"]["current_timestamp"], 0)
    diff = now_timestamp - last_tag_timestamp if last_tag_timestamp > 0 and now_timestamp > 0 else 0
    if diff < CONFIG["params"]["post_tag_lock_seconds"]:
        pause_reason = f"Blocco post-tag per {int(CONFIG['params']['post_tag_lock_seconds'] - diff)}s"
    else:
        state_data = get_system_state(CONFIG)
        if state_data.get("voltage", 0) <= 0:
            pause_reason = f"🔴 ERRORE CRITICO: Voltaggio non valido ({state_data.get('voltage')}V)."
            call_service("select", "select_option", {"entity_id": CONFIG["entities"]["wallbox_set_mode"], "option": "paused"})
        else:
            pause_reason_from_rules = determine_pause_reason(state_data, CONFIG)
            if pause_reason_from_rules:
                final_amps, pause_mode, pause_reason = apply_wallbox_state(0, pause_reason_from_rules, 0, CONFIG)
            else:
                target_amps, calc_pause_reason = calculate_target_amps(state_data, CONFIG)
                last_amp = get_float(CONFIG["entities"]["last_wallbox_current"], 0)
                final_amps, pause_mode, pause_reason = apply_wallbox_state(target_amps, calc_pause_reason, last_amp, CONFIG)

# === BLOCCO FINALE: Aggiornamento sensore di stato ===
execution_time = 0
script_end_iso = get_str(CONFIG["entities"]["date_time_iso"])
if script_start_iso != 'unavailable' and script_end_iso != 'unavailable':
    execution_time = time_diff_seconds_approx(script_end_iso, script_start_iso)

if pause_reason == "Connettore non collegato":
    final_state_str = "🔌 Non Collegato"
    final_icon = "mdi:power-plug-off"
else:
    final_state_str = f"{('⏸️ PAUSA' if pause_mode else '⚡ CARICA')} {final_amps}A"
    final_icon = "mdi:pause" if pause_mode else "mdi:ev-station"

attributes = {
    "pv_power": round(state_data.get("pv_power", 0), 1),
    "pv_primary": round(state_data.get("pv_primary", 0), 1),
    "pv_secondary": round(state_data.get("pv_secondary", 0), 1),
    "secondary_active": state_data.get("inverter_secondary_active", False),
    "home_power": round(state_data.get("home_power", 0), 1),
    "pv_excess": round(state_data.get("pv_excess", 0), 1),
    "batt_power": round(state_data.get("batt_power", 0), 1),
    "soc_attuale": round(state_data.get("soc_attuale", 0), 1),
    "decision_amp": final_amps,
    "pause_mode": pause_mode,
    "pause_reason": pause_reason,
    "last_update": script_end_iso,
    "script_duration": round(execution_time, 3),
    "friendly_name": "Wallbox Status",
    "icon": final_icon,
    "info": "v2025.10.12"
}
try:
    hass.states.set(CONFIG["entities"]["status_sensor"], final_state_str, attributes)
except Exception as e:
    log_always(f"[Wallbox] Errore critico aggiornamento sensore di stato: {e}")

log_debug("[Wallbox] Script TERMINATO")
