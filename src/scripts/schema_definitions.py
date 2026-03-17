from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class FieldDef:
    name: str
    type_name: str  # e.g., "String", "Collection(String)", "DateTimeOffset", "Boolean", "Double"
    searchable: bool = False
    filterable: bool = False
    sortable: bool = False
    # If a field comes from a different key in the JSONL metadata, map it here
    # If it's a list of keys, the first non-null one found is used
    # (e.g. ["best_eta_dp_date", "optimal_ata_dp_date"])
    source_keys: Optional[str | List[str]] = None


SCHEMA_FIELDS = [
    # --- Identifiers & RLS ---
    FieldDef("document_id", "String", filterable=True),
    FieldDef("content", "String", searchable=True),
    FieldDef("consignee_code_ids", "Collection(String)", filterable=True),
    # --- Core Searchable Lookup Arrays ---
    FieldDef("container_number", "String", searchable=True, filterable=True),
    FieldDef("po_numbers", "Collection(String)", searchable=True, filterable=True),
    FieldDef(
        "obl_nos",
        "Collection(String)",
        searchable=True,
        filterable=True,
        source_keys=["obl_nos", "ocean_bl_numbers"],
    ),
    FieldDef("booking_numbers", "Collection(String)", searchable=True, filterable=True),
    FieldDef("fcr_numbers", "Collection(String)", searchable=True, filterable=True),
    # --- Shipment Attributes & Types ---
    FieldDef("job_no", "String", searchable=True, filterable=True),
    FieldDef("job_type", "String", searchable=True, filterable=True),
    FieldDef("container_type", "String", searchable=True, filterable=True),
    FieldDef("destination_service", "String", searchable=True, filterable=True),
    FieldDef("transport_mode", "String", searchable=True, filterable=True),
    FieldDef("shipment_status", "String", searchable=True, filterable=True),
    FieldDef(
        "hot_container_flag",
        "Boolean",
        filterable=True,
        sortable=True,
        source_keys=["hot_container_flag", "hot_container"],
    ),
    # --- Entities / Names ---
    FieldDef("consignee_name", "String", searchable=True, filterable=True),
    FieldDef("supplier_vendor_name", "String", searchable=True, filterable=True),
    FieldDef("manufacturer_name", "String", searchable=True, filterable=True),
    FieldDef("ship_to_party_name", "String", searchable=True, filterable=True),
    FieldDef("first_vessel_name", "String", searchable=True, filterable=True),
    FieldDef("final_carrier_name", "String", searchable=True, filterable=True),
    FieldDef("final_vessel_name", "String", searchable=True, filterable=True),
    FieldDef("final_voyage_code", "String", searchable=True, filterable=True),
    FieldDef("true_carrier_scac_name", "String", searchable=True, filterable=True),
    FieldDef("mcs_hbl", "String", searchable=True, filterable=True),
    # --- Locations ---
    FieldDef("load_port", "String", searchable=True, filterable=True),
    FieldDef("final_load_port", "String", searchable=True, filterable=True),
    FieldDef("discharge_port", "String", searchable=True, filterable=True),
    FieldDef("last_cy_location", "String", searchable=True, filterable=True),
    FieldDef("place_of_receipt", "String", searchable=True, filterable=True),
    FieldDef("place_of_delivery", "String", searchable=True, filterable=True),
    FieldDef("final_destination", "String", searchable=True, filterable=True),
    FieldDef("carrier_vehicle_load_lcn", "String", filterable=True),
    FieldDef("vehicle_departure_lcn", "String", filterable=True),
    FieldDef("vehicle_arrival_lcn", "String", filterable=True),
    FieldDef("carrier_vehicle_unload_lcn", "String", filterable=True),
    FieldDef("out_gate_from_dp_lcn", "String", filterable=True),
    FieldDef("equipment_arrived_at_last_cy_lcn", "String", filterable=True),
    FieldDef("out_gate_at_last_cy_lcn", "String", filterable=True),
    FieldDef("delivery_to_consignee_lcn", "String", filterable=True),
    FieldDef("empty_container_return_lcn", "String", filterable=True),
    FieldDef("in_gate_lcn", "String", filterable=True),
    FieldDef("empty_container_dispatch_lcn", "String", filterable=True),
    # --- Quantities / Metrics ---
    FieldDef("cargo_weight_kg", "Double", filterable=True),
    FieldDef("cargo_measure_cubic_meter", "Double", filterable=True),
    FieldDef("cargo_count", "Double", filterable=True),
    FieldDef("dp_delayed_dur", "Double", filterable=True),
    FieldDef("fd_delayed_dur", "Double", filterable=True),
    # --- Core Dates ---
    FieldDef("etd_lp_date", "DateTimeOffset", filterable=True, sortable=True),
    FieldDef("etd_flp_date", "DateTimeOffset", filterable=True, sortable=True),
    FieldDef("eta_dp_date", "DateTimeOffset", filterable=True, sortable=True),
    FieldDef("eta_fd_date", "DateTimeOffset", filterable=True, sortable=True),
    FieldDef("atd_lp_date", "DateTimeOffset", filterable=True, sortable=True),
    FieldDef("ata_flp_date", "DateTimeOffset", filterable=True, sortable=True),
    FieldDef("atd_flp_date", "DateTimeOffset", filterable=True, sortable=True),
    # For derived / optimum dates, we can map multiple potential source keys
    FieldDef(
        "ata_dp_date",
        "DateTimeOffset",
        filterable=True,
        sortable=True,
        source_keys=["derived_ata_dp_date", "ata_dp_date", "optimal_ata_dp_date"],
    ),
    FieldDef(
        "best_eta_dp_date",
        "DateTimeOffset",
        filterable=True,
        sortable=True,
        source_keys=[
            "best_eta_dp_date",
            "optimal_ata_dp_date",
            "derived_ata_dp_date",
            "ata_dp_date",
        ],
    ),
    FieldDef(
        "best_eta_fd_date",
        "DateTimeOffset",
        filterable=True,
        sortable=True,
        source_keys=[
            "best_eta_fd_date",
            "optimal_eta_fd_date",
            "revised_eta_fd_date",
            "eta_fd_date",
        ],
    ),
    # --- Extended Dates ---
    FieldDef("revised_eta_date", "DateTimeOffset", filterable=True, sortable=True),
    FieldDef("predictive_eta_date", "DateTimeOffset", filterable=True, sortable=True),
    FieldDef("revised_eta_fd_date", "DateTimeOffset", filterable=True, sortable=True),
    FieldDef(
        "predictive_eta_fd_date", "DateTimeOffset", filterable=True, sortable=True
    ),
    FieldDef("in_gate_date", "DateTimeOffset", filterable=True, sortable=True),
    FieldDef(
        "empty_container_dispatch_date",
        "DateTimeOffset",
        filterable=True,
        sortable=True,
    ),
    FieldDef(
        "delivery_to_consignee_date", "DateTimeOffset", filterable=True, sortable=True
    ),
    FieldDef(
        "empty_container_return_date", "DateTimeOffset", filterable=True, sortable=True
    ),
    FieldDef(
        "in_dc_date",
        "DateTimeOffset",
        filterable=True,
        sortable=True,
        source_keys="in-dc_date",
    ),
    # --- Delay & Workarounds ---
    FieldDef("delayed_dp", "String", filterable=True),
    FieldDef("delayed_fd", "String", filterable=True),
    FieldDef("workflow_gap_flags", "String", filterable=True),
    # --- Summaries ---
    FieldDef("critical_dates_summary", "String", searchable=True),
    FieldDef("delay_reason_summary", "String", searchable=True),
    FieldDef("milestones", "String", searchable=True),
    FieldDef("vessel_summary", "String", searchable=True),
    FieldDef("carrier_summary", "String", searchable=True),
    FieldDef("port_route_summary", "String", searchable=True),
]
