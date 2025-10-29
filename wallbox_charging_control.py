"""
'Python_Script Home Assistant per gestione Wallbox con impianto fotovoltaico e batteria senza immissione di corrente in rete.'
'Autore: [bruno[AT]casapiras.it]'
'Wallbox Dynamic Controller v2025.10.29'
Funzionalità Script:
    Lo script utilizza diverse entità di Home Assistant (template o di sistema/integrazioni) per monitorare lo stato della Wallbox.
    Allo stesso tempo riesce a veicolare sulla Wallbox la giusta quantita di corrente tenendo sotto controllo il consummo massimo della casa, 
    la ricarica della batteria FTV e altri valori.
    Viene avviato (dopo essere stato copiato nella cartella /config/python_script) tramite una automazione di Home Assistant ogni X secondi(45 nel mio caso).
Modifiche 29/10/2025:
- ✍️ LOGGING: Implementata la funzione di logging warning per alcuni messaggi importanti.
Modifiche 28/10/2025:
- FEATURE: Aggiunta logica 'predittiva' che stima la produzione FV potenziale per un avvio più rapido e intelligente.
- FEATURE: Aggiunta logica 'attiva' per stimolare la produzione FV a batteria carica e surplus nullo.
- FIX: Corretta la logica 'MAX CHARGE FORZATA' per utilizzare la potenza FV in eccesso reale invece di un valore fisso.
- FEATURE: In caso di scarica eccessiva della batteria, la potenza viene ridotta dinamicamente invece di fermare la carica.
- FEATURE: Aggiunti log di debug dettagliati per tutte le principali decisioni dello script.
- FEATURE: Implementata logica per stimolare l'avvio del secondo inverter 'dormiente' stimando la sua produzione potenziale e aggiungendola al surplus calcolato.
- 🚀 MIGLIORIA: Aggiunta logica di logging estesa in *ogni* punto decisionale critico per una diagnostica completa.
- ⚡ PERFORMANCE: **Ottimizzazione delle chiamate a servizio** rimuovendo `blocking=True` dove non essenziale per evitare rallentamenti del core HA.
- 🧹 REFACTOR: Semplificazione del calcolo della durata dello script tramite timestamp Unix.
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
        "current_timestamp": "sensor.current_timestamp",                            #<-Sensore Template timestamp Unix<>#
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
        "home_max_current": "input_number.wboxmaxhomecurrent",                      #<-Number Corrente massima che l'impianto di casa puo' assorbire (comprende ovviamente anche la Wallbox)<># 
        "wallbox_power": "sensor.silla_prism_output_power",                         #<-Sensore Wallbox PW erogata<>#  
        "ev_soc": "sensor.ev3_ev_battery_level",                                    #<-Sensore Kia SOC Auto (si aggiorna circa ogni 15min)<>#
        "ev_target_soc": "input_number.ev_target_soc",                              #<-Number Target di ricarica Batteria Kia<>#      
        "time": "sensor.time",                                                      #<-Sensore Tempo (HH:MM)<>#    
        "pause_start_time": "input_datetime.wbox_orainizio",                        #<-Input Ora e minuti Inizio Pausa Ricarica<>#    
        "pause_end_time": "input_datetime.wbox_orafine",                            #<-Input Ora e minuti Fine Pausa Ricarica<>#      
        "sun": "sun.sun",                                                           #<-Sensore Sole<>#
        "sun_elevation_threshold": "input_number.wboxelevation",                    #<-Number Elevazione del Sole sotto il quale la logica di ricarica non poarte<>#
        "battery_priority_ratio": "input_number.wbox_battery_priority_ratio",       #<-Number Percentuale di divisione della ricarica tra macchina e batteria casa (quando necessario)<>#    
        "last_wallbox_current": "input_number.last_wallbox_current",                #<-Number Ultima Corrente impostata dallo script<>#
        "date_time_iso": "sensor.date_time_iso",                                    #<-Sensore Template data e ora (per log) <>#
        "last_wbox_tag": "input_datetime.last_wbox_tag",                            #<-Input Ultimo utilizzo TAG Rfid<>#
        "status_sensor": "sensor.wallbox_status"                                    #<-Sensor Template creato e aggiornato dallo Script<>#  
    },
    "params": {
        "post_tag_lock_seconds": 180,                                               #<-Tempo di blocco dopo l'RFID (Scenario 2)<>#
        "stabilization_delta_amp": 1.0,                                             #<-Delta minimo di corrente per l'aggiornamento (Scenario 14)<>#    
        "min_power_ratio_for_min_amps": 0.6,                                        #<-Percentuale di potenza per forzare i min_amp (0.6 = 60%)<>#
        "min_secondary_inverter_power": 20,                                         #<-Soglia per considerare attivo l'inverter secondario<>#
        "batt_discharge_margin": 0.8,                                               #<-Ulteriore margine di sicurezza di scarica batteria 80% del massimo consentito<>#    
        "force_charge_soc_threshold": 95.0,                                         #<-Oltre 95% SOC, forza la carica massima<>#
        "pv_safety_margin_ratio": 0.1,                                              #<-10% di margine sull'eccedenza<>#
        "batt_protection_cycles_on_fault": 3                                        #<-Numero di cicli in cui si evita la logica di Ricarica<>#    
    }
}

# === 2. FUNZIONI HELPER ===

def log_debug(message):
    if DEBUG_MODE:
        logger.info(message)

def log_always(message):
    logger.warning(message)

def get_str(entity_id, default='unavailable'):
    state = hass.states.get(entity_id)
    if state is None:
        log_always(f"[Wallbox] Entità {entity_id} non trovata. Ritorno default '{default}'.")
        return default
    return state.state

def get_float(entity_id, default=0.0, decimals=3):
    state_obj = hass.states.get(entity_id)
    if state_obj is None:
        log_always(f"[Wallbox] Entità {entity_id} non trovata. Ritorno default {default}.")
        return default
    try:
        return round(float(state_obj.state), decimals)
    except (TypeError, ValueError):
        log_always(f"[Wallbox] Valore non numerico per {entity_id}: {state_obj.state} -> uso default {default}")
        return default

def get_float_attr(entity_id, attribute, default=0.0, decimals=3):
    state_obj = hass.states.get(entity_id)
    if state_obj is None:
        log_always(f"[Wallbox] Entità {entity_id} non trovata per l'attributo '{attribute}'. Ritorno default {default}.")
        return default
    val = state_obj.attributes.get(attribute)
    try:
        return round(float(val), decimals)
    except (TypeError, ValueError):
        log_always(f"[Wallbox] Attributo non numerico per {entity_id}.{attribute}: {val} -> uso default {default}")
        return default

def get_attr(entity_id, attribute, default=None):
    state_obj = hass.states.get(entity_id)
    if state_obj is None:
        log_always(f"[Wallbox] Entità {entity_id} non trovata per l'attributo '{attribute}'. Ritorno default.")
        return default
    return state_obj.attributes.get(attribute, default)

def call_service(domain, service, service_data, log_error=True, blocking=False):
    """Chiama un servizio HA. Default non bloccante per performance."""
    try:
        hass.services.call(domain, service, service_data, blocking=blocking)
        return True
    except Exception as e:
        if log_error:
            log_always(f"[Wallbox] Errore chiamata servizio {domain}.{service}: {e}")
        return False

# La funzione time_diff_seconds_approx è stata rimossa

# === 3. LOGICA DELLO SCRIPT ===

def get_system_state(cfg):
    state = {}
    entities = cfg["entities"]
    state["voltage"] = get_float(entities["voltage"])
    state["forzacharge"] = get_str(entities["force_charge"]) == "on"
    state["pv1"] = get_float(entities["pv_primary_1"])
    state["pv2"] = get_float(entities["pv_primary_2"])
    pv_primary = state["pv1"] + state["pv2"]
    pv_secondary = get_float(entities["pv_secondary"])
    state["inverter_secondary_active"] = pv_secondary > cfg["params"]["min_secondary_inverter_power"]
    
    # 🆕 Stimiamo la potenza potenziale del secondario
    pv_potential_secondary = max(state["pv1"], state["pv2"]) 
    state["pv_potential_secondary"] = pv_potential_secondary
    
    log_debug(f"[Wallbox] Inverter Secondario: {'ATTIVO' if state['inverter_secondary_active'] else 'DORM.'} (Soglia: {cfg['params']['min_secondary_inverter_power']}W). PW stimata: {pv_potential_secondary:.1f}W")
    
    pv_lordo = pv_primary + pv_secondary
    
    state["pv_power"] = pv_lordo - get_float(entities["pv_losses"])
    state["pv_primary"] = pv_primary
    state["pv_secondary"] = pv_secondary
    state["batt_power"] = get_float(entities["batt_power"])
    state["batt_max_discharge"] = get_float(entities["batt_max_discharge"])
    state["soc_attuale"] = get_float(entities["batt_soc"])
    state["soc_min"] = get_float(entities["batt_soc_min"])
    state["soc_priority"] = get_float(entities["batt_soc_priority"])
    home_power = get_float(entities["home_power"])
    wallbox_power = get_float(entities["wallbox_power"], 0)
    home_domestic_power = max(0, home_power - wallbox_power)
    state["wallbox_power"] = wallbox_power
    state["home_domestic_power"] = home_domestic_power
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
    
    log_debug(f"[Wallbox] STATO: PV Totale={state['pv_power']:.1f}W, Domestico={home_domestic_power:.1f}W, Excess={state['pv_excess']:.1f}W, Batt SOC={state['soc_attuale']:.1f}%, Voltage={state['voltage']:.1f}V")
    return state

def determine_pause_reason(state, cfg):
    entities = cfg["entities"]
    params = cfg["params"]
    
    # SCENARIO 1: Carica Forzata
    if state["forzacharge"]:
        log_debug("[Wallbox] 🟢 SCENARIO 1: Carica forzata attiva. Ignoro tutte le pause.")
        return None
        
    # SCENARIO 2: EV Target Raggiunto
    if state["ev_soc"] >= state["ev_target"]:
        log_debug(f"[Wallbox] ⏸️ SCENARIO 2: EV SOC target raggiunto ({state['ev_soc']:.1f}% >= {state['ev_target']:.1f}%).")
        return f"EV SOC target raggiunto ({state['ev_soc']:.1f}%)"
        
    # SCENARIO 3: Consumo Casa Eccessivo
    if state["home_current"] > state["home_max_current"]:
        log_debug(f"[Wallbox] ⏸️ SCENARIO 3: Consumo casa eccessivo ({state['home_current']:.1f}A > {state['home_max_current']:.1f}A).")
        return f"Consumo casa eccessivo: {state['home_current']:.1f}A > {state['home_max_current']:.1f}A"
        
    # SCENARIO 4: Finestra di Pausa (Orari)
    ora_inizio, ora_fine, ora_attuale = state["ora_inizio_pausa"], state["ora_fine_pausa"], state["ora_attuale"]
    if (ora_inizio < ora_fine and ora_inizio <= ora_attuale <= ora_fine) or \
       (ora_inizio > ora_fine and (ora_attuale >= ora_inizio or ora_attuale <= ora_fine)):
        log_debug(f"[Wallbox] ⏸️ SCENARIO 4: Finestra di pausa oraria attiva ({ora_inizio}-{ora_fine}).")
        return f"Finestra di pausa attiva ({ora_inizio}-{ora_fine})"
        
    # SCENARIO 5: SOC Batteria Critico
    if state["soc_attuale"] < state["soc_min"]:
        log_debug(f"[Wallbox] ⏸️ SCENARIO 5: SOC batteria critico ({state['soc_attuale']:.1f}% < {state['soc_min']:.1f}%).")
        return f"SOC batteria critico: {state['soc_attuale']:.1f}% < {state['soc_min']:.1f}%"
        
    # SCENARIO 6: Protezione Cicli Batteria
    batt_protection_cycles = get_float(entities["batt_protection_cycles"], 0)
    if batt_protection_cycles > 0:
        new_cycles = max(0, batt_protection_cycles - 1)
        # ⚡ Mantenuto blocking=True per garantire che il ciclo venga ridotto prima del prossimo trigger
        call_service("input_number", "set_value", {"entity_id": entities["batt_protection_cycles"], "value": new_cycles}, blocking=True)
        log_debug(f"[Wallbox] ⏸️ SCENARIO 6: Protezione batteria attiva ({int(batt_protection_cycles)} -> {new_cycles} cicli rimanenti).")
        return f"Protezione batteria attiva ({int(batt_protection_cycles)} cicli rimanenti)"
        
    # SCENARIO 7: Nessuna Pausa Forzata da Regole
    log_debug("[Wallbox] ➡️ SCENARIO 7: Nessuna regola di pausa bloccante attiva. Procedo al calcolo della potenza.")
    return None

def calculate_target_amps(state, cfg):
    params = cfg["params"]
    available_power = 0
    pause_reason = None
    
    # SCENARIO 8: Sole Basso (Pre-requisito)
    if state["sun_elevation"] < state["elevation_limit"] and not state["is_rising"]:
        log_debug(f"[Wallbox] ⏸️ SCENARIO 8: Sole basso in discesa ({state['sun_elevation']:.1f}° < {state['elevation_limit']:.1f}°).")
        pause_reason = f"Sole basso in discesa ({state['sun_elevation']:.1f}°)"
        
    # SCENARIO 9: Gestione Scarica Batteria Eccessiva (Riduzione Dinamica)
    elif not state["forzacharge"] and state["batt_power"] > (state["batt_max_discharge"] * params["batt_discharge_margin"]):
        discharge_limit = state["batt_max_discharge"] * params["batt_discharge_margin"]
        over_discharge_watts = state["batt_power"] - discharge_limit
        new_target_power = state["wallbox_power"] - over_discharge_watts - 50 # 50W buffer
        
        log_debug(f"[Wallbox] 📉 SCENARIO 9: Scarica batteria eccessiva ({state['batt_power']:.1f}W > {discharge_limit:.1f}W). Riduco PW a {int(new_target_power)}W.")
        available_power = new_target_power
        
    # SCENARIO 10-13: Logiche di Calcolo Potenza
    else:
        # Aggiunta dello Stimolo Inverter Secondario
        pv_excess_with_stimulus = state["pv_excess"]
        stimulus_power = 0
        
        if not state["inverter_secondary_active"] and \
           state["soc_attuale"] >= state["soc_min"] and \
           state["pv_potential_secondary"] > state["min_wallbox_power"]:
            
            stimulus_power = state["pv_potential_secondary"]
            pv_excess_with_stimulus += stimulus_power
            log_debug(f"[Wallbox] 💡 Stimolo Inverter Sec. Aggiungo {stimulus_power:.1f}W (Excess stimolato: {pv_excess_with_stimulus:.1f}W).")

        effective_excess = pv_excess_with_stimulus
        
        # SCENARIO 10: Batteria Sotto SOC Minimo (Non Critico)
        if state["soc_attuale"] < state["soc_min"]:
            log_debug(f"[Wallbox] ⏸️ SCENARIO 10: SOC Batteria ({state['soc_attuale']:.1f}%) sotto il minimo ({state['soc_min']:.1f}%). PW disponibile = 0W.")
            available_power = 0
            
        # SCENARIO 11: Priorità Batteria (SOC tra Min e Priority)
        elif state["soc_min"] <= state["soc_attuale"] < state["soc_priority"]:
            if effective_excess >= state["min_wallbox_power"]: 
                excess_after_min = effective_excess - state["min_wallbox_power"]
                excess_for_batt = excess_after_min * (state["batt_priority_ratio"] / 100.0)
                available_power = state["min_wallbox_power"] + (excess_after_min - excess_for_batt)
                log_debug(f"[Wallbox] ⚖️ SCENARIO 11: Priorità Batteria. PW Totale={effective_excess:.1f}W. PW WBox={available_power:.1f}W (6A+rest). PW Batt={excess_for_batt:.1f}W.")
            else:
                log_debug(f"[Wallbox] ⏸️ SCENARIO 11a: Priorità Batteria. Excess stimolato insufficiente ({effective_excess:.1f}W < {state['min_wallbox_power']:.1f}W). PW disponibile = 0W.")
                available_power = 0
                
        # SCENARIO 12: Batteria Carica / SOC Alto (Modalità Eco Pura o Stimolo)
        else:
            # SCENARIO 12a: SOC Batteria molto alto (Forza Max)
            if state["soc_attuale"] > params["force_charge_soc_threshold"]:
                log_debug(f"[Wallbox] ⚡ SCENARIO 12a: SOC Batteria molto alto ({state['soc_attuale']:.1f}%). Forzo Max Charge.")
                if effective_excess >= state["min_wallbox_power"]:
                    available_power = effective_excess
                    log_debug(f"[Wallbox] Max Charge: Uso surplus ({available_power:.1f}W).")
                else:
                    available_power = state["min_wallbox_power"] 
                    log_debug(f"[Wallbox] Max Charge: Surplus nullo. Avvio carica minima ({available_power:.1f}W) per stimolo.")
            # SCENARIO 12b: SOC Normale (Usa l'eccedenza con Margine)
            elif effective_excess >= state["min_wallbox_power"]:
                safety_margin = effective_excess * params["pv_safety_margin_ratio"]
                available_power = effective_excess - safety_margin
                log_debug(f"[Wallbox] ⚡ SCENARIO 12b: Excess sufficiente. PW Netta={available_power:.1f}W (Excess={effective_excess:.1f}W - Margin={safety_margin:.1f}W).")
            # SCENARIO 12c: Excess Insufficiente
            else:
                log_debug(f"[Wallbox] ⏸️ SCENARIO 12c: Excess stimolato insufficiente ({effective_excess:.1f}W < {state['min_wallbox_power']:.1f}W). PW disponibile = 0W.")
                available_power = 0
    
    # Calcolo Amperaggio Finale
    clamped_amp = 0
    if available_power > 0:
        available_amp = available_power / state["voltage"]
        
        # SCENARIO 13: Sufficiente per Min_Amp (e oltre)
        if available_amp >= state["min_amp"]:
            clamped_amp = int(round(max(state["min_amp"], min(state["max_amp"], available_amp))))
            log_debug(f"[Wallbox] ⚡ SCENARIO 13: PW ({available_power:.1f}W) sufficiente. Imposto {clamped_amp}A.")
        
        # SCENARIO 13a: Potenza Vicina a Min_Amp (Forza Min_Amp)
        elif available_power >= (state["min_wallbox_power"] * params["min_power_ratio_for_min_amps"]):
            clamped_amp = int(state["min_amp"])
            log_debug(f"[Wallbox] ⚠️ SCENARIO 13a: PW calcolata ({available_power:.1f}W) è > {params['min_power_ratio_for_min_amps'] * 100}% del minimo. Forza {state['min_amp']}A.")
    
    # SCENARIO 14: Pausa per Corrente Troppo Bassa
    if clamped_amp < state["min_amp"]:
        clamped_amp = 0
        if not pause_reason:
             pause_reason = "Corrente calcolata troppo bassa"
             log_debug(f"[Wallbox] ⏸️ SCENARIO 14: Corrente calcolata ({available_amp:.1f}A) < Min_Amp ({state['min_amp']}A). Messa in pausa.")

    return clamped_amp, pause_reason

def apply_wallbox_state(target_amps, pause_reason, last_amp, cfg):
    entities = cfg["entities"]
    params = cfg["params"]
    
    # SCENARIO 15: Applicazione Pausa
    if pause_reason:
        log_debug(f"[Wallbox] 🛑 SCENARIO 15: Applico Pausa ({pause_reason}). Set Mode: 'paused'.")
        # ⚡ Chiamata non bloccante
        call_service("select", "select_option", {"entity_id": entities["wallbox_set_mode"], "option": "paused"})
        return 0, True, pause_reason
        
    final_amps = target_amps
    
    # SCENARIO 16: Stabilizzazione Corrente
    if target_amps > 0 and last_amp > 0:
        delta = abs(target_amps - last_amp)
        if delta < params["stabilization_delta_amp"]:
            final_amps = last_amp
            log_debug(f"[Wallbox] 🔄 SCENARIO 16: Stabilizzazione. Target {target_amps}A, Delta {delta:.1f}A < {params['stabilization_delta_amp']}A. Mantengo {final_amps}A.")
    
    # SCENARIO 17: Applicazione Carica
    log_debug(f"[Wallbox] 🚀 SCENARIO 17: Applico Carica. Corrente finale impostata a {final_amps}A. Set Mode: 'normal'.")
    # ⚡ Chiamate non bloccanti
    call_service("number", "set_value", {"entity_id": entities["wallbox_set_current"], "value": final_amps})
    call_service("input_number", "set_value", {"entity_id": entities["last_wallbox_current"], "value": final_amps})
    call_service("select", "select_option", {"entity_id": entities["wallbox_set_mode"], "option": "normal"})
    return final_amps, False, "Carica attiva"

# === 4. ESECUZIONE PRINCIPALE ===

DEBUG_MODE = get_str(CONFIG["entities"]["debug_mode"]) == "on"
# ⚡ Raccolgo il timestamp di inizio per il calcolo della durata
script_start_timestamp = get_float(CONFIG["entities"]["current_timestamp"], 0)
log_debug(f"[Wallbox] Script AVVIATO v2025.10.29 - Debug: {'ATTIVO' if DEBUG_MODE else 'DISATTIVO'}")
final_amps, pause_mode, pause_reason, state_data = 0, True, "", {}

# CONTROLLO PRELIMINARE: Connettore
if get_str(CONFIG["entities"]["wallbox_state"]) == "idle":
    pause_reason = "Connettore non collegato"
    # Cambiato da log_debug a log_debug
    log_debug("[Wallbox] 🔌 Controllo Preliminare: Connettore IDLE.")
else:
    # CONTROLLO PRELIMINARE: Blocco RFID
    last_tag_timestamp = get_float_attr(CONFIG["entities"]["last_tag_time"], "timestamp", 0)
    now_timestamp = get_float(CONFIG["entities"]["current_timestamp"], 0)
    diff = now_timestamp - last_tag_timestamp if last_tag_timestamp > 0 and now_timestamp > 0 else 0
    if diff < CONFIG["params"]["post_tag_lock_seconds"]:
        pause_reason = f"Blocco post-tag per {int(CONFIG['params']['post_tag_lock_seconds'] - diff)}s"
        log_debug(f"[Wallbox] ⏸️ Controllo Preliminare: Blocco post-tag attivo. Tempo rimanente: {int(CONFIG['params']['post_tag_lock_seconds'] - diff)}s.")
    else:
        state_data = get_system_state(CONFIG)
        
        # CONTROLLO PRELIMINARE: Voltaggio Critico
        if state_data.get("voltage", 0) <= 0:
            pause_reason = f"🔴 ERRORE CRITICO: Voltaggio non valido ({state_data.get('voltage')}V)."
            # ⚡ Chiamata non bloccante
            call_service("select", "select_option", {"entity_id": CONFIG["entities"]["wallbox_set_mode"], "option": "paused"})
            log_always(f"[Wallbox] 🔴 Controllo Preliminare: Voltaggio Critico. ({state_data.get('voltage', 0)}V).")
        else:
            # ESECUZIONE LOGICHE PRINCIPALI
            pause_reason_from_rules = determine_pause_reason(state_data, CONFIG)
            if pause_reason_from_rules:
                final_amps, pause_mode, pause_reason = apply_wallbox_state(0, pause_reason_from_rules, 0, CONFIG)
            else:
                target_amps, calc_pause_reason = calculate_target_amps(state_data, CONFIG)
                last_amp = get_float(CONFIG["entities"]["last_wallbox_current"], 0)
                final_amps, pause_mode, pause_reason = apply_wallbox_state(target_amps, calc_pause_reason, last_amp, CONFIG)

# === BLOCCO FINALE: Aggiornamento sensore di stato ===
script_end_iso = get_str(CONFIG["entities"]["date_time_iso"])
script_end_timestamp = get_float(CONFIG["entities"]["current_timestamp"], 0)

execution_time = 0
if script_start_timestamp > 0 and script_end_timestamp > 0:
    execution_time = script_end_timestamp - script_start_timestamp

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
    "pv_potential_secondary": round(state_data.get("pv_potential_secondary", 0), 1),
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
    "info": "v2025.10.29"
}
try:
    hass.states.set(CONFIG["entities"]["status_sensor"], final_state_str, attributes)
except Exception as e:
    log_always(f"[Wallbox] Errore critico aggiornamento sensore di stato: {e}")

log_debug("[Wallbox] Script TERMINATO")