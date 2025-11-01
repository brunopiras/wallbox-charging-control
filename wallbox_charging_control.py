"""
Wallbox Dynamic Controller
Versione: 2025.11.0
"""

# === 1. CONFIGURAZIONE CENTRALE ===
CONFIG = {
    "entities": {
        "debug_mode": "input_boolean.wboxdebug",
        "voltage": "sensor.silla_prism_power_grid_voltage",
        "wallbox_state": "sensor.silla_prism_current_state",
        "current_timestamp": "sensor.current_timestamp",
        "wallbox_set_mode": "select.silla_prism_set_mode",
        "wallbox_set_current": "number.silla_prism_set_max_current",
        "last_tag_time": "input_datetime.last_wbox_tag",
        "pv_primary_1": "sensor.deyeha_pv1_power",
        "pv_primary_2": "sensor.deyeha_pv2_power",
        "pv_secondary": "sensor.inverter_lcd_pv_power",
        "pv_total": "sensor.deye_pv_power",
        "pv_losses": "sensor.deyeha_power_losses",
        "batt_power": "sensor.tdt_bms_power_inverted",
        "batt_max_discharge": "input_number.battmaxdischarge",
        "batt_soc": "sensor.deyeha_battery",
        "batt_soc_min": "input_number.wboxsocmin",
        "batt_soc_priority": "input_number.wboxsocchargepriority",
        "batt_protection_cycles": "input_number.wallbox_batt_protection_cycles",
        "min_charge_amps": "input_number.wboxminamp",
        "max_charge_amps": "input_number.wboxmaxamp",
        "force_charge": "input_boolean.wboxforzacharge",
        "home_power": "sensor.green_power",
        "home_current": "sensor.green_current",
        "home_max_current": "input_number.wboxmaxhomecurrent",
        "wallbox_power": "sensor.silla_prism_output_power",
        "ev_soc": "sensor.ev3_ev_battery_level",
        "ev_target_soc": "input_number.ev_target_soc",
        "ev_soc_emergenza": "input_number.ev_soc_emergenza",
        "time": "sensor.time",
        "pause_start_time": "input_datetime.wbox_orainizio",
        "pause_end_time": "input_datetime.wbox_orafine",
        "sun": "sun.sun",
        "sun_elevation_threshold": "input_number.wboxelevation",
        "battery_priority_ratio": "input_number.wbox_battery_priority_ratio",
        "last_wallbox_current": "input_number.last_wallbox_current",
        "date_time_iso": "sensor.date_time_iso",
        "last_wbox_tag": "input_datetime.last_wbox_tag",
        "status_sensor": "sensor.wallbox_status",
        "grid": "binary_sensor.deyeha_grid"
    },
    "params": {
        "post_tag_lock_seconds": 180,
        "stabilization_delta_amp": 1.0,
        "min_power_ratio_for_min_amps": 0.7,
        "min_secondary_inverter_power": 20,
        "batt_discharge_margin": 0.8,
        "force_charge_soc_threshold": 95.0,
        "pv_safety_margin_ratio": 0.1,
        "batt_protection_cycles_on_fault": 3,
        "buffer_watts_on_discharge_reduce": 50,
        "min_amp_default": 6
    }
}

# === 2. HELPERS I/O e LOGGING ===
def debug_enabled():
    try:
        s = hass.states.get(CONFIG["entities"]["debug_mode"])
        return s is not None and str(s.state).lower() == "on"
    except Exception:
        return False

def log_debug(msg):
    try:
        if debug_enabled():
            logger.info(f"[Wallbox DEBUG V 2025.11.0] {msg}")
    except Exception:
        logger.info("[Wallbox DEBUG V 2025.11.0] (log error)")

def log_warn(msg):
    try:
        logger.warning(f"[Wallbox DEBUG V 2025.11.0] {msg}")
    except Exception:
        pass

def get_state_obj(entity_id):
    try:
        return hass.states.get(entity_id)
    except Exception:
        return None

def get_str(entity_id, default='unavailable'):
    s = get_state_obj(entity_id)
    if s is None:
        log_warn(f"Entità {entity_id} non trovata. Uso default '{default}'.")
        return default
    return s.state

def get_float(entity_id, default=0.0, decimals=3):
    s = get_state_obj(entity_id)
    if s is None:
        log_warn(f"Entità {entity_id} non trovata. Uso default {default}.")
        return default
    try:
        return round(float(s.state), decimals)
    except Exception:
        log_warn(f"Valore non numerico per {entity_id}: {s.state} -> uso default {default}")
        return default

def get_float_attr(entity_id, attribute, default=0.0, decimals=3):
    s = get_state_obj(entity_id)
    if s is None:
        log_warn(f"Entità {entity_id} non trovata per attributo '{attribute}'. Uso default {default}.")
        return default
    try:
        val = s.attributes.get(attribute)
        return round(float(val), decimals)
    except Exception:
        log_warn(f"Attributo non numerico per {entity_id}.{attribute}: {s.attributes.get(attribute)} -> uso default {default}")
        return default

def get_attr(entity_id, attribute, default=None):
    s = get_state_obj(entity_id)
    if s is None:
        return default
    return s.attributes.get(attribute, default)

def get_bool(entity_id, default=False):
    s = get_state_obj(entity_id)
    if s is None:
        return default
    v = s.state
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("on", "true", "1", "yes")

def call_service(domain, service, data, log_error=True, blocking=False):
    """
    Compatibile con python_script: non passiamo il keyword 'blocking' a hass.services.call
    (in alcuni ambienti la firma non accetta il keyword).
    Se necessario in futuro si può ripristinare comportamento diverso per altre integrazioni.
    """
    try:
        # Non passare blocking come keyword per compatibilità con python_script
        hass.services.call(domain, service, data)
        return True
    except Exception as e:
        if log_error:
            log_warn(f"Errore chiamata servizio {domain}.{service}: {e}")
        return False

# === HELPERS NOTIFICHE ===
def send_persistent_notification(notification_id, title, message, priority="info"):
    try:
        service_data = {
            "notification_id": f"wallbox_{notification_id}",
            "title": title,
            "message": message
        }
        hass.services.call("persistent_notification", "create", service_data)
        log_debug(f"Notifica persistente inviata: {notification_id}")
        return True
    except Exception as e:
        log_warn(f"Errore invio notifica {notification_id}: {e}")
        return False

def dismiss_persistent_notification(notification_id):
    try:
        entity_id = f"persistent_notification.wallbox_{notification_id}"
        # Controlla se esiste lo stato della notifica prima di chiamare il servizio
        if hass.states.get(entity_id) is None:
            #log_debug(f"[Wallbox] Nessuna notifica persistente da rimuovere: {notification_id}")
            return True
        service_data = {"notification_id": f"wallbox_{notification_id}"}
        hass.services.call("persistent_notification", "dismiss", service_data)
        log_debug(f"Notifica rimossa: {notification_id}")
        return True
    except Exception as e:
        log_warn(f"Errore rimozione notifica {notification_id}: {e}")
        return False

# === 3. LETTURA STATO ===
def get_system_state(cfg):
    e = cfg["entities"]
    p = cfg["params"]
    s = {}

    s["voltage"] = get_float(e["voltage"])
    s["forzacharge"] = get_bool(e["force_charge"])
    s["pv1"] = get_float(e["pv_primary_1"])
    s["pv2"] = get_float(e["pv_primary_2"])
    s["pv_primary"] = s["pv1"] + s["pv2"]
    s["pv_secondary"] = get_float(e["pv_secondary"])
    s["pv_losses"] = get_float(e["pv_losses"])
    pv_lordo = s["pv_primary"] + s["pv_secondary"]
    s["pv_power"] = max(0.0, pv_lordo - s["pv_losses"])
    s["batt_power"] = get_float(e["batt_power"])
    s["batt_max_discharge"] = get_float(e["batt_max_discharge"])
    s["soc_attuale"] = get_float(e["batt_soc"])
    s["soc_min"] = get_float(e["batt_soc_min"])
    s["soc_priority"] = get_float(e["batt_soc_priority"])
    s["home_power"] = get_float(e["home_power"])
    s["wallbox_power"] = get_float(e["wallbox_power"], 0)
    s["home_domestic_power"] = max(0.0, s["home_power"] - s["wallbox_power"])
    s["home_current"] = get_float(e["home_current"])
    s["home_max_current"] = get_float(e["home_max_current"])
    s["pv_excess"] = s["pv_power"] - s["home_domestic_power"]

    # EV SOC: None se sensore non disponibile (non forziamo 100 di default)
    ev_obj = get_state_obj(e["ev_soc"])
    if ev_obj is None:
        s["ev_soc"] = None
    else:
        try:
            s["ev_soc"] = round(float(ev_obj.state), 1)
        except Exception:
            s["ev_soc"] = None

    s["ev_target"] = get_float(e["ev_target_soc"])
    s["ev_soc_emergenza"] = get_float(e["ev_soc_emergenza"], default=0.0)

    s["ora_attuale"] = get_str(e["time"])[:5]
    s["ora_inizio_pausa"] = get_str(e["pause_start_time"], "00:00:00")[:5]
    s["ora_fine_pausa"] = get_str(e["pause_end_time"], "00:00:00")[:5]

    s["sun_elevation"] = get_float_attr(e["sun"], "elevation")
    # CORRETTO: leggere attributo rising (booleano) invece di usare lo stato testuale
    s["is_rising"] = bool(get_attr(e["sun"], "rising", False))
    s["elevation_limit"] = get_float(e["sun_elevation_threshold"])

    # garantiamo min_amp minimo
    s["min_amp"] = max(p.get("min_amp_default", 6), get_float(e["min_charge_amps"]) or p.get("min_amp_default", 6))
    s["max_amp"] = get_float(e["max_charge_amps"])
    s["min_wallbox_power"] = s["min_amp"] * s["voltage"]
    s["batt_priority_ratio"] = get_float(e["battery_priority_ratio"])

    s["inverter_secondary_active"] = s["pv_secondary"] > p["min_secondary_inverter_power"]
    #s["pv_potential_secondary"] = max(s["pv1"], s["pv2"])
    s["pv_potential_secondary"] = s["pv1"]
    s["grid_present"] = get_bool(e["grid"], True)

    s["timestamp"] = get_float(e["current_timestamp"], 0)

    log_debug("STATO LETTO: PV={:.1f}W Excess={:.1f}W BattPW={:.1f}W SOC={:.1f}% MinPW={:.1f}W".format(
        s["pv_power"], s["pv_excess"], s["batt_power"], s["soc_attuale"], s["min_wallbox_power"]))
    return s

# === 4. CONTROLLI PRELIMINARI ===
def controlli_preliminari(cfg):
    e = cfg["entities"]
    p = cfg["params"]

    if get_str(e["wallbox_state"]) == "idle":
        return "Connettore non collegato"

    last_tag_ts = get_float_attr(e["last_tag_time"], "timestamp", 0)
    now_ts = get_float(e["current_timestamp"], 0)
    diff = (now_ts - last_tag_ts) if (last_tag_ts and now_ts and last_tag_ts > 0) else 0
    if diff and diff < p["post_tag_lock_seconds"]:
        remaining = int(p["post_tag_lock_seconds"] - diff)
        return f"Blocco post-tag per {remaining}s"

    return None

# === 5. DETERMINA RAGIONI DI PAUSA (SCENARI 0..7) ===
def determine_pause_reason(state, cfg):
    e = cfg["entities"]
    p = cfg["params"]

    # Emergency EV: sensore deve essere disponibile
    ev_soc = state.get("ev_soc")
    ev_emerg = state.get("ev_soc_emergenza", 0.0)
    is_emergency = False
    if (ev_soc is not None) and ev_emerg and ev_soc < ev_emerg and ev_soc < 99.0:
        is_emergency = True
        log_warn(f"SCENARIO 0 (EMERGENZA EV): EV SOC {ev_soc}% < soglia {ev_emerg}%")
        send_persistent_notification(
            "ev_emergency",
            "🚨 Emergenza EV - Carica Forzata",
            f"EV SOC critico: {ev_soc}% (soglia: {ev_emerg}%). Carica minima forzata.",
            "error"
        )

    # SCENARIO 1: Forza carica -> niente pause
    if state.get("forzacharge"):
        log_debug("SCENARIO 1: Carica forzata attiva")
        return None

    # SCENARIO 2: EV target raggiunto
    if (ev_soc is not None) and ev_soc >= state.get("ev_target", 0):
        return f"EV SOC target raggiunto ({ev_soc:.1f}%)"

    # SCENARIO 3: Consumo casa eccessivo
    if state.get("home_current", 0) > state.get("home_max_current", 0):
        return f"Consumo casa eccessivo: {state['home_current']:.1f}A > {state['home_max_current']:.1f}A"

    # SCENARIO 4: Finestra di pausa (oraria)
    start = state.get("ora_inizio_pausa")
    end = state.get("ora_fine_pausa")
    now = state.get("ora_attuale")
    try:
        if (start < end and start <= now <= end) or (start > end and (now >= start or now <= end)):
            if is_emergency:
                log_debug("SCENARIO 4: Pausa oraria bypassata per emergenza EV")
            else:
                return f"Finestra di pausa attiva ({start}-{end})"
    except Exception:
        pass

    # SCENARIO 5: SOC batteria critico
    if state.get("soc_attuale", 100) < state.get("soc_min", 0):
        if is_emergency:
            log_debug("SCENARIO 5: SOC batteria critico bypassato per emergenza EV")
        else:
            return f"SOC batteria critico: {state['soc_attuale']:.1f}% < {state['soc_min']:.1f}%"

    # SCENARIO 6: Protezione cicli batteria
    cycles = get_float(e["batt_protection_cycles"], 0)
    if cycles > 0:
        new_cycles = max(0, int(cycles) - 1)
        # Non passiamo blocking al servizio per compatibilità
        call_service("input_number", "set_value", {"entity_id": e["batt_protection_cycles"], "value": new_cycles})
        log_debug(f"SCENARIO 6: Protezione batteria attiva ({int(cycles)} -> {new_cycles} cicli rimanenti).")
        return f"Protezione batteria attiva ({new_cycles} cicli rimanenti)"

    # SCENARIO 7: Nessuna pausa forzata
    log_debug("SCENARIO 7: Nessuna regola di pausa bloccante attiva")
    return None

# === 6. CALCOLO POTENZA / AMPERE (SCENARI 8..13) ===
def calculate_target_amps(state, cfg):
    p = cfg["params"]
    available_power = 0.0   # INIZIALIZZIAMO A 0 per evitare None-behaviour
    pause_reason = None

    ev_soc = state.get("ev_soc")
    ev_emerg = state.get("ev_soc_emergenza", 0.0)
    is_emergency = (ev_soc is not None and ev_emerg and ev_soc < ev_emerg and ev_soc < 99.0)

    # SCENARIO 8: Sole basso (pre-condizione per mettere in pausa)
    if state.get("sun_elevation", 0) < state.get("elevation_limit", 0) and not state.get("is_rising", True):
        log_debug(f"SCENARIO 8: Sole basso in discesa ({state.get('sun_elevation'):.1f}° < {state.get('elevation_limit'):.1f}°).")
        # Non return immediato: permettiamo a emergenza EV (8a) di bypassare la pausa
        if not is_emergency:
            pause_reason = f"Sole basso in discesa ({state.get('sun_elevation'):.1f}°)"
            # available_power rimane 0 -> verrà trasformato in pausa successivamente

    # SCENARIO 8a: Emergenza EV -> forza min_amp e bypass pausa oraria/SOC
    if is_emergency:
        log_warn(f"SCENARIO 8a: Emergenza EV -> forzo carica minima {state.get('min_amp')}A")
        available_power = state.get("min_wallbox_power", state.get("min_amp", p.get("min_amp_default",6)) * state.get("voltage", 230))
        # invio notifica gestita già in determine_pause_reason (se necessario)
        # Non sovrascriviamo pause_reason se la emergenza deve bypassarla

    # SCENARIO 9: Scarica batteria eccessiva -> riduzione dinamica (solo se non forzato)
    if (not state.get("forzacharge", False)) and state.get("batt_power", 0) > (state.get("batt_max_discharge", 0) * p["batt_discharge_margin"]):
        if state.get("pv_excess", 0) < 100 or state.get("soc_attuale", 0) < state.get("soc_priority", 0):
            discharge_limit = state.get("batt_max_discharge", 0) * p["batt_discharge_margin"]
            over_discharge_watts = state.get("batt_power") - discharge_limit
            new_target_power = state.get("wallbox_power", 0) - over_discharge_watts - p.get("buffer_watts_on_discharge_reduce", 50)
            available_power = max(0.0, new_target_power)
            log_debug(f"SCENARIO 9: Scarica batteria eccessiva -> nuova PW {available_power:.1f}W")

    # SCENARIO 10-12: logiche basate su excess e SOC (solo se available_power non ancora deciso dall'emergenza o scarica eccessiva)
    if available_power <= 0:
        effective_excess = state.get("pv_excess", 0.0)

        # Stimolo inverter secondario
        if (not state.get("inverter_secondary_active")) and state.get("soc_attuale", 0) >= state.get("soc_min", 0) and state.get("pv_potential_secondary", 0) > state.get("min_wallbox_power", 0):
            stimulus_power = state.get("pv_potential_secondary", 0)
            effective_excess += stimulus_power
            log_debug(f"Stimolo inverter secondario: aggiungo {stimulus_power:.1f}W (Excess stimolato: {effective_excess:.1f}W)")

        # SCENARIO 10: SOC sotto min -> nessuna carica
        if state.get("soc_attuale", 0) < state.get("soc_min", 0):
            log_debug("SCENARIO 10: SOC Batteria sotto min -> PW disponibile = 0W")
            available_power = 0.0

        # SCENARIO 11: Priorità Batteria (tra min e priority)
        elif state.get("soc_min", 0) <= state.get("soc_attuale", 0) < state.get("soc_priority", 0):
            if effective_excess >= state.get("min_wallbox_power", 0):
                excess_after_min = effective_excess - state.get("min_wallbox_power")
                excess_for_batt = excess_after_min * (state.get("batt_priority_ratio", 0) / 100.0)
                available_power = state.get("min_wallbox_power") + (excess_after_min - excess_for_batt)
                log_debug(f"SCENARIO 11: PW Wallbox={available_power:.1f}W, PW Batt={excess_for_batt:.1f}W")
            else:
                log_debug(f"SCENARIO 11a: Excess insufficiente ({effective_excess:.1f}W) -> PW=0")
                available_power = 0.0

        # SCENARIO 12: Batteria carica / SOC alto o normale
        else:
            # SCENARIO 12a: SOC molto alto -> forza max charge
            if state.get("soc_attuale", 0) > p["force_charge_soc_threshold"]:
                if effective_excess >= state.get("min_wallbox_power", 0):
                    available_power = effective_excess
                    log_debug(f"SCENARIO 12a: Max Charge usando surplus {available_power:.1f}W")
                else:
                    min_power_threshold = state.get("min_wallbox_power", 0) * p["min_power_ratio_for_min_amps"]
                    if effective_excess >= min_power_threshold:
                        available_power = state.get("min_wallbox_power", 0)
                        log_debug(f"SCENARIO 12a-bis: Excess {effective_excess:.1f}W > soglia {min_power_threshold:.1f}W -> forzo carica minima")
                    else:
                        available_power = 0.0
                        log_debug(f"SCENARIO 12a-ter: Excess insufficiente ({effective_excess:.1f}W) -> PW=0")
            # SCENARIO 12b: SOC normale, excess sufficiente
            elif effective_excess >= state.get("min_wallbox_power", 0):
                safety_margin = effective_excess * p["pv_safety_margin_ratio"]
                available_power = max(0.0, effective_excess - safety_margin)
                log_debug(f"SCENARIO 12b: Excess sufficiente -> PW netta {available_power:.1f}W (margin {safety_margin:.1f}W)")
            # SCENARIO 12c: Excess inferiore al minimo ma sopra soglia di attivazione
            else:
                min_power_threshold = state.get("min_wallbox_power", 0) * p["min_power_ratio_for_min_amps"]
                if effective_excess >= min_power_threshold:
                    available_power = state.get("min_wallbox_power", 0)
                    log_debug(f"SCENARIO 12c-bis: Excess {effective_excess:.1f}W > soglia {min_power_threshold:.1f}W -> forzo carica minima")
                else:
                    log_debug(f"SCENARIO 12c: Excess insufficiente ({effective_excess:.1f}W) -> PW=0")
                    available_power = 0.0

    # Conversione in ampere e clamp
    clamped_amp = 0
    if available_power is not None and available_power > 0 and state.get("voltage", 0) > 0:
        available_amp = available_power / state["voltage"]
        if available_amp >= state.get("min_amp", p.get("min_amp_default", 6)):
            clamped_amp = int(round(max(state.get("min_amp", p.get("min_amp_default",6)), min(state.get("max_amp", 32), available_amp))))
            log_debug(f"SCENARIO 13: PW {available_power:.1f}W -> {available_amp:.1f}A -> imposto {clamped_amp}A")
        else:
            # Se la potenza calcolata è inferiore al minimo ma sopra la soglia di attivazione -> forzo min_amp
            min_power_threshold = state.get("min_wallbox_power", 0) * p["min_power_ratio_for_min_amps"]
            if available_power >= min_power_threshold:
                clamped_amp = int(state.get("min_amp", p.get("min_amp_default",6)))
                log_debug(f"SCENARIO 13a: PW {available_power:.1f}W > soglia {min_power_threshold:.1f}W -> forzo {clamped_amp}A")
            else:
                clamped_amp = 0
                if available_power is not None:
                    pause_reason = f"Potenza calcolata troppo bassa ({available_power:.1f}W)"

    # Requisito aggiuntivo: wallbox non accetta valore inferiore al min_amp -> in quel caso PAUSA
    if clamped_amp > 0 and clamped_amp < state.get("min_amp", p.get("min_amp_default",6)):
        log_debug(f"Ampere calcolati ({clamped_amp}A) < min_amp ({state.get('min_amp')}A) -> imposto pausa")
        clamped_amp = 0
        if not pause_reason:
            pause_reason = f"Ampere calcolati inferiori al minimo richiesto ({state.get('min_amp')}A)"

    return clamped_amp, pause_reason

# === 7. APPLICA STATO ALLA WALLBOX ===
def apply_wallbox_state(target_amps, pause_reason, cfg):
    e = cfg["entities"]
    p = cfg["params"]

    # Se target_amps è 0 O c'è una ragione di pausa -> METTI IN PAUSA
    if pause_reason or target_amps == 0:
        log_debug(f"SCENARIO 15: Applico pausa -> {pause_reason or 'Potenza insufficiente'}")
        call_service("select", "select_option", {"entity_id": e["wallbox_set_mode"], "option": "paused"})
        return 0, True, pause_reason or "Potenza insufficiente"

    # Stabilizzazione
    last_amp = get_float(e["last_wallbox_current"], 0)
    final_amps = target_amps
    if target_amps > 0 and last_amp > 0:
        if abs(target_amps - last_amp) < p["stabilization_delta_amp"]:
            final_amps = int(last_amp)
            log_debug(f"SCENARIO 16: Stabilizzazione -> mantengo {final_amps}A")

    # Verifica che final_amps sia >= min_amp (wallbox non accetta inferiore)
    if final_amps < state_local.get("min_amp", p.get("min_amp_default",6)):
        log_debug(f"SCENARIO 17a: Ampere insufficienti ({final_amps}A) -> pausa")
        call_service("select", "select_option", {"entity_id": e["wallbox_set_mode"], "option": "paused"})
        return 0, True, "Ampere insufficienti"

    # Applicazione corrente
    log_debug(f"SCENARIO 17: Applico carica -> impostati {final_amps}A")
    call_service("number", "set_value", {"entity_id": e["wallbox_set_current"], "value": final_amps})
    call_service("input_number", "set_value", {"entity_id": e["last_wallbox_current"], "value": final_amps})
    call_service("select", "select_option", {"entity_id": e["wallbox_set_mode"], "option": "normal"})
    return final_amps, False, "Carica attiva"

# Note: apply_wallbox_state needs min_amp value; to avoid passing state everywhere we will keep a wrapper that passes state_local

# === 8. AGGIORNA SENSORE DI STATO ===
def update_status_sensor(final_amps, pause_mode, pause_reason, state_data, cfg, start_ts, end_ts):
    e = cfg["entities"]
    execution_time = 0
    if start_ts and end_ts:
        execution_time = end_ts - start_ts

    if pause_reason == "Connettore non collegato":
        final_state_str = "🔌 Non Collegato"
        final_icon = "mdi:power-plug-off"
    else:
        final_state_str = f"{('⏸️ PAUSA' if pause_mode else '⚡ CARICA')} {final_amps}A"
        final_icon = "mdi:pause" if pause_mode else "mdi:ev-station"

    attrs = {
        "Rete Elettrica": "Connessa" if state_data.get("grid_present", True) else "Disconnessa",
        "Power FTV": round(state_data.get("pv_power", 0), 1),
        "Deye Stringa EST": round(state_data.get("pv_primary", 0), 1),
        "Deye Stringa OVEST": round(state_data.get("pv_secondary", 0), 1),
        "Inverter Genius": state_data.get("inverter_secondary_active", False),
        "Genius PW Prevista": round(state_data.get("pv_potential_secondary", 0), 1),
        "PW Casa": round(state_data.get("home_power", 0), 1),
        "PW Solare Eccesso": round(state_data.get("pv_excess", 0), 1),
        "PW Batteria": round(state_data.get("batt_power", 0), 1),
        "SOC Casa": round(state_data.get("soc_attuale", 0), 1),
        "Amp. -> Wallbox": final_amps,
        "Pausa": "SI" if pause_mode else "NO",
        "Ragione Pausa": pause_reason or "",
        "Ult. Aggiornamento": get_str(e["date_time_iso"]),
        "Durata Script": round(execution_time, 3),
        "icon": final_icon,
        "Nome Sensore": "Wallbox Status",
        "info": "v2025.11.0"
    }
    try:
        hass.states.set(e["status_sensor"], final_state_str, attrs)
    except Exception as exc:
        log_warn(f"Errore nell'aggiornamento del sensore di stato: {exc}")

# === 9. RUNNER PRINCIPALE ===
def main():
    global state_local
    start_ts = get_float(CONFIG["entities"]["current_timestamp"], 0)
    dt_iso_start = get_str(CONFIG["entities"]["date_time_iso"], "")
    try:
        start_time_hms = dt_iso_start.split("T")[1][:8] if "T" in dt_iso_start else dt_iso_start[-8:]
    except Exception:
        start_time_hms = dt_iso_start
    log_debug(f"Script AVVIATO - inizio {start_time_hms}")

    # Controlli preliminari
    pre = controlli_preliminari(CONFIG)
    if pre:
        human_reason = pre
        end_ts = get_float(CONFIG["entities"]["current_timestamp"], 0)
        call_service("select", "select_option", {"entity_id": CONFIG["entities"]["wallbox_set_mode"], "option": "paused"})
        state_min = {"grid_present": True}
        update_status_sensor(0, True, human_reason, state_min, CONFIG, start_ts, end_ts)
        return

    # Lettura stato completo
    state = get_system_state(CONFIG)
    state_local = state  # salvo globalmente per apply_wallbox_state controllo min_amp

    # Controllo voltaggio
    if state.get("voltage", 0) <= 0:
        call_service("select", "select_option", {"entity_id": CONFIG["entities"]["wallbox_set_mode"], "option": "paused"})
        log_warn(f"ERRORE CRITICO: Voltaggio non valido ({state.get('voltage')}V).")
        update_status_sensor(0, True, f"Voltaggio non valido ({state.get('voltage')}V)", state, CONFIG, start_ts, get_float(CONFIG["entities"]["current_timestamp"], 0))
        return

    # Controllo critico: grid assente e batteria bassa
    if (not state.get("grid_present", True)) and state.get("soc_attuale", 100) < state.get("soc_min", 0):
        call_service("select", "select_option", {"entity_id": CONFIG["entities"]["wallbox_set_mode"], "option": "paused"})
        log_warn("GRID ASSENTE e SOC batteria sotto minimo -> metto in pausa")
        send_persistent_notification(
            "grid_absent_battery_low",
            "⚠️ Grid Assente - Carica Bloccata",
            f"La rete elettrica è assente e la batteria di casa è bassa ({state.get('soc_attuale')}%). La ricarica della Wallbox è stata sospesa.",
            "warning"
        )
        update_status_sensor(0, True, "GRID assente e batt. bassa", state, CONFIG, start_ts, get_float(CONFIG["entities"]["current_timestamp"], 0))
        return

    # Logiche principali: pause e calcolo ampere
    pause_from_rules = determine_pause_reason(state, CONFIG)
    if pause_from_rules:
        final_amps, pause_mode, pause_reason = apply_wallbox_state(0, pause_from_rules, CONFIG)
    else:
        target_amps, calc_pause_reason = calculate_target_amps(state, CONFIG)
        final_amps, pause_mode, pause_reason = apply_wallbox_state(target_amps, calc_pause_reason, CONFIG)

    # Aggiorna sensore di stato
    end_ts = get_float(CONFIG["entities"]["current_timestamp"], 0)
    update_status_sensor(final_amps, pause_mode, pause_reason, state, CONFIG, start_ts, end_ts)

    # --- Pulizia notifiche condizionata ---
    # Evitiamo di rimuovere notifiche che devono rimanere visibili finché la condizione è ancora vera.

    # EV EMERGENCY: rimuovi solo se emergenza non è più attiva
    ev_soc = state.get("ev_soc")              # None se sensore assente (fallback prudente)
    ev_emerg_threshold = state.get("ev_soc_emergenza", 0.0)
    ev_emergency_active = False
    if ev_soc is not None and ev_emerg_threshold and ev_soc < ev_emerg_threshold and ev_soc < 99.0:
        ev_emergency_active = True

    if ev_emergency_active:
        log_debug(f"[Wallbox DEBUG V 2025.11.0] Mantengo notifica EV_EMERGENCY: EV SOC {ev_soc} < soglia {ev_emerg_threshold}")
    else:
        # dismiss_persistent_notification controlla già l'esistenza della notifica prima di rimuovere
        dismiss_persistent_notification("ev_emergency")

    # GRID ABSENT + BATTERY LOW: rimuovi solo se la condizione critica è risolta
    grid_present = state.get("grid_present", True)
    soc_attuale = state.get("soc_attuale", 100)
    soc_min = state.get("soc_min", 0)

    grid_critical_active = (not grid_present) and (soc_attuale < soc_min)

    if grid_critical_active:
        log_debug(f"[Wallbox DEBUG V 2025.11.0] Mantengo notifica GRID_ABSENT_BATTERY_LOW: grid_present={grid_present}, SOC={soc_attuale}% < min {soc_min}%")
    else:
        dismiss_persistent_notification("grid_absent_battery_low")

    duration = round(end_ts - start_ts, 3) if start_ts and end_ts else None
    readable_pause = "PAUSA" if pause_mode else "CARICA"

    if duration is not None:
        log_debug(f"Script TERMINATO - {readable_pause} {final_amps}A - motivo: {pause_reason or 'Nessuno'} - durata {duration}s")
    else:
        log_debug(f"Script TERMINATO - {readable_pause} {final_amps}A - motivo: {pause_reason or 'Nessuno'}")

# Esegui
main()