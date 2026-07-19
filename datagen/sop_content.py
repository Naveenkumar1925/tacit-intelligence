"""SOP text content for the Plant Brain corpus generator.

Eight procedures, 800-1200 words each (verified by generate_corpus.py).
SOP-114 carries the monthly strainer-cleaning statement for Pattern 4
(divergence vs. the fortnightly-during-monsoon voice claims).

Entity-messiness note (spec 6.6): procedures deliberately write the pump
tag as "Pump 101A" (not "P-101A") so entity resolution has work to do.
Revision dates use DD/MM/YYYY, work orders use YYYY-MM-DD (spec 6.6).
"""

SOPS = [
    {
        "sop_id": "SOP-101",
        "title": "Centrifugal Pump Startup and Shutdown Procedure",
        "revision": "Rev 4",
        "rev_date": "12/03/2025",
        "applies_to": ["P-101A", "P-101B", "P-101C", "P-102A", "P-102B", "P-103A"],
        "sections": [
            ("Purpose", [
                "This procedure defines the approved method for starting up and shutting down the centrifugal "
                "process pumps installed in the Process Area and the Utilities Area of Plant Site A. Correct "
                "startup practice protects the mechanical seal, the bearings and the driver from avoidable "
                "damage, and ensures that flow is established in a controlled manner without water hammer or "
                "cavitation. Shutdown practice ensures the pump is left in a safe, drained or preserved state.",
            ]),
            ("Scope", [
                "This procedure applies to all centrifugal pumps in the plant equipment register, including "
                "Pump 101A, Pump 101B and Pump 101C in the Process Area, and the cooling water pumps "
                "P-102A, P-102B and P-103A in the Utilities Area. It covers routine operational starts and "
                "planned shutdowns. It does not cover first commissioning, post-overhaul acceptance testing, "
                "or emergency trips, which are addressed in the relevant maintenance and operations manuals.",
            ]),
            ("References", [
                "SOP-114 Centrifugal Pump Suction Strainer Maintenance.",
                "SOP-110 Rotating Equipment Vibration Monitoring and Bearing Lubrication.",
                "SOP-118 Equipment Isolation and Lock-Out Tag-Out.",
                "Manufacturer operating manual for the installed pump model, held in the technical library.",
            ]),
            ("Safety Precautions", [
                "Confirm that no isolation tags or locks are present on the pump, its driver or its switchgear "
                "before attempting a start. If a tag is present, stop and contact the shift supervisor.",
                "Never run a centrifugal pump against a closed suction valve. Never run the pump dry, even "
                "briefly, as the mechanical seal faces will be destroyed within seconds.",
                "Stand clear of the coupling guard during starting. Hearing protection is required in the pump "
                "bay when any machine in the bay is running.",
            ]),
            ("Tools and Materials", [
                "Routine starting requires no special tools. Have available a clean lint-free rag, the "
                "approved lubricant grade for top-up, a torch for sight glass inspection, hearing protection, "
                "and the shift log or work tablet for recording readings.",
                "For a first start following maintenance, additionally obtain the handover documentation and "
                "the signed-off isolation certificate, and confirm with the shift supervisor that the permit "
                "is closed and every lock and tag has been removed from the driver and the switchgear.",
            ]),
            ("Procedure - Startup", [
                "Walk down the pump and confirm the general condition: no loose fasteners, no oil on the "
                "baseplate, coupling guard secured, and no visible damage to instrument tubing or cabling.",
                "Where the coupling was disturbed during maintenance, bump the motor uncoupled and verify "
                "rotation against the direction arrow before engaging the coupling and continuing with the "
                "start checks.",
                "Check the bearing housing oil level at the sight glass. The level shall sit at the centre of "
                "the sight glass with the pump stopped. Top up with the approved lubricant grade if required.",
                "Verify the suction strainer differential pressure gauge reads below the limit given in "
                "SOP-114. A blinded strainer at start is a common cause of immediate cavitation.",
                "Open the suction valve fully. Crack the casing vent until a steady liquid stream is observed, "
                "confirming the casing is flooded and vapour free, then close the vent.",
                "Confirm the seal flush line block valves are open and the seal pot level, where fitted, is "
                "between the marked limits. Confirm cooling or quench services to the bearing housings are "
                "lined up and flowing where fitted; a pump started without its quench can run correctly for "
                "minutes and then fail hours later, which is far harder to diagnose.",
                "Close the discharge valve to the minimum-flow position marked on the valve stem, or fully "
                "closed where the pump has an automatic minimum-flow recirculation line.",
                "Start the driver. Observe the discharge pressure gauge; pressure should rise promptly to the "
                "expected shut-in value. If pressure does not develop within ten seconds, stop the pump and "
                "investigate loss of prime.",
                "Open the discharge valve slowly over thirty to sixty seconds while watching motor current, "
                "until the normal operating flow is established. Avoid running for more than two minutes at "
                "the closed-valve condition.",
                "Check the mechanical seal area for leakage, feel the bearing housings for unusual warmth, and "
                "listen for cavitation, which presents as a sound like gravel passing through the pump.",
                "Record the startup in the shift log, noting discharge pressure, motor current and any "
                "abnormal observation, and update the running-hours board for the pump train.",
            ]),
            ("Procedure - Shutdown", [
                "For a planned shutdown, first close the discharge valve to roughly one-quarter open to reduce "
                "load, then stop the driver at the local station.",
                "After the pump coasts down, close the discharge valve fully. Leave the suction valve open "
                "unless the pump is being handed over to maintenance.",
                "If the pump is to be handed to maintenance, isolate and drain in accordance with SOP-118 and "
                "hang the appropriate tags before any work begins.",
                "For standby pumps in autostart service, confirm the autostart selector is returned to the "
                "correct position and the pump remains flooded via the open suction valve.",
                "Record the shutdown and the final running hours in the shift log, and note whether duty has "
                "transferred to the standby unit; if so, complete the standby start checks in full rather "
                "than assuming the machine will start on demand.",
            ]),
            ("Acceptance Criteria", [
                "The pump is considered successfully started when discharge pressure and motor current are "
                "steady at their normal values, seal leakage is nil, and bearing housing temperature "
                "stabilises below 70 degrees C within thirty minutes. Any vibration judged abnormal shall be "
                "reported and assessed against SOP-110 before the pump is left in unattended service.",
            ]),
            ("Records", [
                "Startup and shutdown events shall be recorded in the shift log. Abnormal observations shall "
                "be raised as work requests in the maintenance system quoting the pump tag and this "
                "procedure number.",
            ]),
        ],
    },
    {
        "sop_id": "SOP-103",
        "title": "Mechanical Seal Inspection and Replacement - Process Pumps",
        "revision": "Rev 2",
        "rev_date": "28/11/2024",
        "applies_to": ["P-101A", "P-101B", "P-101C", "P-102A", "P-102B", "P-103A"],
        "sections": [
            ("Purpose", [
                "This procedure defines the approved method for inspecting and replacing cartridge mechanical "
                "seals on the horizontal centrifugal process pumps at Plant Site A. Seal leakage is the single "
                "most frequent corrective maintenance driver on the pump fleet, and disciplined seal work "
                "directly reduces repeat failures and unplanned downtime.",
            ]),
            ("Scope", [
                "Applies to cartridge-type mechanical seals fitted to the process transfer pumps, including "
                "Pump 101A and its sister units, and to the utilities cooling water pumps. Gland packed "
                "auxiliary pumps are excluded. This procedure covers replacement in the field with the pump "
                "casing in place; full overhauls are performed in the workshop under separate instructions.",
            ]),
            ("References", [
                "SOP-118 Equipment Isolation and Lock-Out Tag-Out.",
                "SOP-101 Centrifugal Pump Startup and Shutdown Procedure.",
                "Seal manufacturer installation drawing for the fitted seal model and size.",
                "API 682 guidance on seal flush plans, held in the technical library.",
            ]),
            ("Safety Precautions", [
                "The pump shall be isolated, drained, depressurised and tagged in accordance with SOP-118 "
                "before the coupling guard is removed. Verify zero energy at the local start station.",
                "Process residues may be present in the seal chamber. Wear the gloves and face shield "
                "specified in the area PPE matrix while breaking containment.",
                "Support the removed seal cartridge; do not allow it to hang on the shaft sleeve, as the "
                "faces crack easily under shock.",
            ]),
            ("Tools and Materials", [
                "Have available before breaking containment: the replacement cartridge seal checked against "
                "the seal drawing for model and size, a dial indicator with magnetic base, feeler gauges, a "
                "calibrated torque wrench covering the gland nut range, new sleeve and gland gaskets, "
                "approved solvent and lint-free rags, fine emery cloth, laser or dial alignment equipment, "
                "and a containment tray sized for the casing volume.",
                "Confirm the correct work order and pump tag at the machine before starting. The A, B and C "
                "units of a pump set are visually identical, and seal work on the wrong unit of a running "
                "set is a recurring industry incident.",
            ]),
            ("Procedure", [
                "Confirm isolation per SOP-118 and verify the casing is drained and vented. Remove the "
                "coupling spacer and the coupling guard, and check shaft end float against the record card.",
                "Before disturbing the seal, inspect and photograph the as-found condition. Note the leakage "
                "path: face leakage, sleeve gasket leakage and gland gasket leakage have different causes and "
                "the distinction matters for the failure record.",
                "Where this is the second seal failure on the same tag inside twelve months, involve the "
                "reliability engineer before fitting the new seal. Fitting another seal into an uncorrected "
                "fault condition wastes both the seal and the outage.",
                "Measure and record seal chamber run-out with a dial indicator. Run-out above 0.05 mm total "
                "indicator reading must be corrected before a new seal is fitted, or the new seal will fail "
                "early for the same reason as the old one.",
                "Remove the seal gland nuts, back off the cartridge setting clips, and withdraw the seal "
                "cartridge along the shaft sleeve. Bag and tag the old seal for failure examination.",
                "Inspect the shaft sleeve under the seal for fretting, scoring or corrosion. Polish minor "
                "marks with fine emery; replace the sleeve if damage can be felt with a fingernail.",
                "Clean the seal chamber thoroughly. Confirm the flush port is clear by blowing instrument air "
                "through the line, and inspect the flush piping for blockage or crushed tubing. Check the "
                "flush orifice size against the piping specification while the line is open, and verify the "
                "flush flow direction matches the seal plan arrow on the drawing.",
                "Fit the new cartridge seal square to the shaft, torque the gland nuts evenly in a cross "
                "pattern to the value on the seal drawing, and only then release the setting clips.",
                "Rotate the shaft by hand through two full turns after fitting the seal and before refitting "
                "the coupling. Any rub or tight spot indicates the seal is cocked or a gasket is displaced, "
                "and shall be corrected before the guard is refitted.",
                "Refit the coupling, verify alignment within 0.05 mm offset and 0.05 mm per 100 mm "
                "angularity, and refit the guard.",
                "Restore the flush plan: open flush line valves, refill the seal pot where fitted, and vent "
                "the seal chamber through the gland vent connection until liquid appears.",
                "Return the pump to service per SOP-101. Observe the seal for the first thirty minutes of "
                "operation; a correctly installed seal shows no visible leakage after an initial weep during "
                "the first minutes of running.",
            ]),
            ("Acceptance Criteria", [
                "The replacement is accepted when the pump runs at normal duty with zero visible seal "
                "leakage, seal flush flow is confirmed, and bearing vibration is unchanged from the pre-work "
                "baseline. The old seal condition and the measured run-out shall be recorded on the work "
                "order before it is closed.",
            ]),
            ("Records", [
                "Complete the work order with the failure code, the as-found seal condition, run-out "
                "readings, the new seal serial number and the downtime hours. Photographs shall be attached "
                "to the equipment history file for the pump tag. Seal failures achieving less than twelve "
                "months of running life shall additionally be reported to the reliability engineer so that "
                "repeat failure patterns on the same tag are visible and investigated.",
            ]),
        ],
    },
    {
        "sop_id": "SOP-105",
        "title": "Shell-and-Tube Heat Exchanger Cleaning and Inspection",
        "revision": "Rev 3",
        "rev_date": "05/06/2025",
        "applies_to": ["HX-201A", "HX-201B", "HX-202A"],
        "sections": [
            ("Purpose", [
                "This procedure defines the method for isolating, opening, cleaning and inspecting the "
                "shell-and-tube heat exchangers at Plant Site A. Fouling of the tube bundle is the dominant "
                "cause of lost thermal performance and of overheating events on downstream equipment, and "
                "periodic cleaning restores the design heat transfer coefficient.",
            ]),
            ("Scope", [
                "Applies to exchangers HX-201A and HX-201B in the Process Area and HX-202A in the Utilities "
                "Area. It covers routine mechanical cleaning of the tube side and shell side, visual "
                "inspection, and return to service. Retubing, plugging beyond ten percent of tubes, and "
                "pressure test failures are escalated to the static equipment engineer.",
            ]),
            ("References", [
                "SOP-118 Equipment Isolation and Lock-Out Tag-Out.",
                "Exchanger general arrangement and tube layout drawings for the unit being worked.",
                "TEMA standards guidance section, held in the technical library.",
            ]),
            ("Safety Precautions", [
                "Both shell side and tube side shall be isolated, drained, depressurised and proven dead "
                "before any flange is broken. Hot condensate hazards persist long after isolation; verify "
                "metal temperature is below 45 degrees C before starting work.",
                "Channel head and floating head covers are heavy eccentric loads. Use the davit or certified "
                "rigging; never support a head on the stud threads.",
                "High pressure water jetting above 250 bar shall only be performed by certified operators "
                "inside a barricaded exclusion zone.",
            ]),
            ("Tools and Materials", [
                "Have available: the davit or certified rigging with current test certificates, hydraulic "
                "torque equipment covering the flange stud sizes, the bolting table for the unit, new "
                "gaskets of the specified material for every joint to be broken, tube cleaning lances and "
                "nozzles matched to the tube bore, a borescope, rated blanking spades for the isolation, and "
                "trays and drums for the deposits removed. High pressure jetting units shall carry a current "
                "inspection certificate, and operator certification shall be verified before work starts.",
                "Verify the exchanger identity against the work order before isolation. HX-201A and HX-201B "
                "sit side by side in the structure, and opening the in-service unit of the pair is a "
                "serious incident.",
            ]),
            ("Procedure", [
                "Confirm isolation of all four nozzles per SOP-118, drain both sides to the closed drain "
                "system, and vent. Verify zero pressure at the vent and drain before unbolting.",
                "Remove the channel head cover using the davit. Inspect the channel, partition plate and "
                "gasket faces for erosion, corrosion and gasket imprint condition, and photograph as found.",
                "Record the as-found fouling: estimate the percentage of tube ends blocked and the deposit "
                "type, whether soft biological film, hard scale, or process polymer. This record drives the "
                "cleaning interval review.",
                "Clean the tube side by high pressure water jetting each tube with the correct nozzle size, "
                "working the full tube length in both directions until the lance passes freely and returns "
                "clear water.",
                "Where shell side cleaning is scheduled, remove the bundle with the certified bundle puller "
                "and jet the outside of the bundle on the wash pad, taking care not to bend tube ends or "
                "displace baffle spacers.",
                "Retain a sample of the removed deposit in a labelled container and estimate the volume "
                "removed. Deposit analysis distinguishes cooling water scale from process side polymer and "
                "directs the correct treatment response.",
                "Inspect a minimum of ten percent of tubes by borescope after cleaning. Look for pitting, "
                "grooving at baffle locations, and inlet-end erosion. Report wall loss findings to the "
                "static equipment engineer.",
                "Renew all gaskets with the material and rating specified on the drawing. Reused gaskets are "
                "not permitted under any circumstance.",
                "Reassemble the heads and torque the flange studs in the star pattern to the values in the "
                "bolting table, in a minimum of three passes at thirty, seventy and one hundred percent.",
                "Before the leak test, verify every temporary blank and spade installed for the work has "
                "been removed and is accounted for on the isolation certificate. A forgotten spade "
                "discovered at recommissioning costs the full outage again.",
                "Perform a leak test at normal operating pressure during recommissioning, checking every "
                "disturbed joint with the shell and channel vents cracked to displace air.",
                "Return the exchanger to service slowly, warming through over at least thirty minutes to "
                "avoid thermal shock to the tubesheet joints. During warm through, walk the unit and check "
                "each disturbed joint; a joint that seeps during warm up will usually reseat as the gasket "
                "beds, but any joint that streams shall be reported and the unit taken off load before "
                "retorquing. Record the post-cleaning terminal temperatures at steady state.",
            ]),
            ("Acceptance Criteria", [
                "Cleaning is accepted when all scheduled tubes pass the lance freely, the borescope sample "
                "shows no defect requiring engineering disposition, the reassembled unit is leak free at "
                "operating pressure, and the approach temperature has recovered to within ten percent of the "
                "clean design value.",
            ]),
            ("Records", [
                "Complete the inspection record with the as-found fouling estimate, tubes plugged, gasket "
                "batch numbers and the post-return thermal performance readings. File the record against "
                "the exchanger tag with a valid-until date per the inspection schedule. Retain the deposit "
                "sample analysis with the record; successive analyses justify changes to the cleaning "
                "interval and to the chemical treatment programme.",
            ]),
        ],
    },
    {
        "sop_id": "SOP-108",
        "title": "Control Valve Calibration and Stroke Testing",
        "revision": "Rev 2",
        "rev_date": "19/02/2025",
        "applies_to": ["CV-301A", "CV-302A", "CV-303A"],
        "sections": [
            ("Purpose", [
                "This procedure defines the method for functional checking, stroke testing and calibration "
                "of the pneumatically actuated control valves at Plant Site A. Accurate valve response "
                "underpins stable process control, and a drifting positioner or sticking stem is a common "
                "hidden cause of process upsets that are wrongly blamed on upstream equipment.",
            ]),
            ("Scope", [
                "Applies to control valves CV-301A and CV-302A in the Process Area and CV-303A in the "
                "Utilities Area, including their positioners, air sets and limit switches. Safety shutdown "
                "valves and relief devices are explicitly excluded and are covered by the safety instrumented "
                "system test procedures.",
            ]),
            ("References", [
                "SOP-118 Equipment Isolation and Lock-Out Tag-Out.",
                "Valve data sheet and positioner calibration manual for the tag under test.",
                "Instrument loop drawing for the associated control loop.",
            ]),
            ("Safety Precautions", [
                "Agree the test with the panel operator before moving any valve. A valve stroked without "
                "warning can trip the unit or divert flow unexpectedly.",
                "Where the valve must be tested in line, confirm the bypass is available and the process "
                "consequence of full stroking has been assessed by the shift supervisor.",
                "Keep hands clear of the yoke and stem at all times. Actuator spring force is sufficient to "
                "sever a finger, and the valve may move without warning while connected to its controller.",
            ]),
            ("Tools and Materials", [
                "Have available: a calibrated signal source or agreed use of the panel output, a calibrated "
                "gauge set for supply air and positioner output, the valve data sheet and positioner manual "
                "for the tag, packing gland spanners, a stopwatch for fail action timing, and the "
                "calibration record sheets. All test equipment shall carry current calibration labels "
                "traceable to the site standard.",
                "Verify the valve tag plate against the work order and the loop drawing before touching "
                "anything. Adjacent valves in the rack share actuator types, and stroking the wrong valve "
                "upsets a healthy loop.",
                "Confirm the panel operator is in continuous radio contact for the duration of the test. If "
                "contact is lost mid stroke, return the valve to its last agreed position and suspend the "
                "test until contact is restored.",
            ]),
            ("Procedure", [
                "Place the control loop in manual at the panel and confirm with the panel operator that the "
                "process is lined up to tolerate valve movement, or that the valve is isolated with the "
                "bypass carrying flow.",
                "Record the as-found condition: supply air pressure at the air set, positioner input and "
                "output gauge readings, and the valve position indicated against the panel output.",
                "Check the air supply quality at the air set drain. Water or oil discharged at the drain "
                "indicates instrument air contamination and shall be reported, because it will drift every "
                "positioner on the header, not only this one.",
                "Apply control signals of zero, twenty five, fifty, seventy five and one hundred percent "
                "from the panel or a signal source, and record the actual stem travel at each point in "
                "both the rising and falling directions.",
                "Compute the hysteresis as the largest difference between rising and falling travel at the "
                "same signal. Hysteresis above two percent of span indicates packing friction or a worn "
                "positioner linkage and shall be corrected, not calibrated around.",
                "Inspect the stem and packing area for leakage, scoring and paint transfer that indicates "
                "rubbing. Adjust packing gland nuts only enough to stop leakage; over-tightening is the "
                "usual cause of stiction. If stiction cannot be corrected by packing adjustment, record the "
                "observed stick slip amplitude and raise the valve for workshop overhaul rather than "
                "compensating by widening the controller dead band.",
                "Verify the positioner zero and span: the valve shall just reach its seat at zero percent "
                "signal and just reach full travel at one hundred percent. Adjust per the positioner manual "
                "and repeat the five-point check after any adjustment.",
                "Confirm the failure action by isolating the air supply and observing the valve move to its "
                "specified fail position within the expected time. Restore the air supply afterwards.",
                "Exercise the limit switches, where fitted, and confirm the open and closed indications "
                "display correctly at the panel. Where switch indication disagrees with the observed valve "
                "position, correct the switch setting rather than the panel graphic, and record the "
                "as-found discrepancy on the calibration sheet.",
                "Return the loop to automatic in coordination with the panel operator and observe the loop "
                "for five minutes to confirm stable control at the normal setpoint.",
            ]),
            ("Acceptance Criteria", [
                "The valve is accepted when travel error at every check point is within one percent of "
                "span, hysteresis is within two percent, the fail action operates correctly, and the loop "
                "holds a steady setpoint in automatic. Any valve failing these criteria shall be reported "
                "with the as-found data on the work order for trending.",
            ]),
            ("Records", [
                "Record as-found and as-left five-point data, hysteresis, air set pressure and fail action "
                "result on the calibration sheet, and file against the valve tag. Trends of successive "
                "calibrations identify valves that are wearing and drive overhaul decisions. Records shall "
                "additionally be reviewed whenever the associated control loop shows sustained oscillation "
                "or steady state offset, before any controller retuning is attempted.",
            ]),
        ],
    },
    {
        "sop_id": "SOP-110",
        "title": "Rotating Equipment Vibration Monitoring and Bearing Lubrication",
        "revision": "Rev 5",
        "rev_date": "22/01/2025",
        "applies_to": ["P-101A", "P-101B", "P-101C", "P-102A", "P-102B", "P-103A"],
        "sections": [
            ("Purpose", [
                "This procedure defines the routine vibration monitoring programme and the bearing "
                "lubrication practice for rotating equipment at Plant Site A. Rising vibration is the "
                "earliest practical warning of bearing distress, misalignment, unbalance and cavitation, "
                "and a disciplined monthly route converts sudden failures into planned work.",
            ]),
            ("Scope", [
                "Applies to all pumps in the equipment register, including the process transfer pumps and "
                "the utilities cooling water pumps such as P-102A, together with their electric motor "
                "drivers. Machines with permanently installed online monitoring are read from the system "
                "but still receive the manual route for confirmation.",
            ]),
            ("References", [
                "ISO 10816 vibration severity guidance, held in the technical library.",
                "SOP-101 Centrifugal Pump Startup and Shutdown Procedure.",
                "Lubrication schedule and approved lubricants list for Plant Site A.",
            ]),
            ("Safety Precautions", [
                "Take readings with the machine at normal steady duty. Do not reach past rotating elements "
                "to place the probe; every measurement point is accessible outside the guard.",
                "Wear hearing protection in the pump bay. If a machine sounds audibly distressed, do not "
                "linger to complete the route; report it immediately.",
                "When greasing with the machine running, use the extension hose and stand clear of the "
                "coupling plane.",
            ]),
            ("Tools and Materials", [
                "Have available: the portable vibration analyser with accelerometer and magnetic mount, "
                "charged and loaded with the current month's route, the stethoscope probe, the grease gun "
                "charged with the approved grade for the machines on the route, clean rags, the lubrication "
                "schedule, and hearing protection. Verify the analyser against the reference check source "
                "before starting the route each month.",
                "Use the same marked measurement point every month. Paint dot each bearing position; "
                "readings taken a few centimetres apart on the same casing differ enough to corrupt the "
                "trend and mask genuine change.",
            ]),
            ("Procedure", [
                "Follow the monthly route in the route list order. At each machine, measure vibration "
                "velocity in millimetres per second RMS at the drive end and non-drive end bearings, in "
                "horizontal, vertical and axial directions.",
                "Take readings only at steady normal duty. A pump throttled for process reasons reads "
                "differently, and a reading captured during transient operation shall be flagged or retaken "
                "rather than entered silently into the trend.",
                "Record each reading against the machine tag and point identifier in the route logger. "
                "Never round or estimate; the trend matters more than the single value.",
                "Compare each reading against the ISO 10816 zone boundaries for the machine class. "
                "Readings in zone C require a work request within one week; readings in zone D require "
                "the machine to be reported for shutdown assessment the same shift.",
                "Compare the reading against the previous three months. A rise of more than fifty percent "
                "over baseline is reportable even if the absolute value remains inside zone B, because "
                "rate of change is the stronger failure signal.",
                "Where a reading is elevated, capture a spectrum. Bearing defect frequencies, running "
                "speed harmonics from misalignment, and blade pass energy from cavitation each present "
                "distinctly, and the spectrum directs the correct maintenance response.",
                "Where cavitation is suspected from the spectrum or from the audible gravel noise, check "
                "the suction strainer differential pressure per SOP-114 before condemning the pump "
                "hydraulics. A choked strainer reproduces every classic cavitation symptom and is "
                "corrected in an hour.",
                "Listen to each bearing with the stethoscope probe. A dry rumble that varies with speed "
                "indicates lubrication starvation and shall be corrected the same day.",
                "Grease motor bearings at the interval and quantity shown in the lubrication schedule "
                "using only the approved grease grade. Wipe the fitting before connecting, and grease "
                "slowly with the relief port open until clean grease appears.",
                "Do not over-grease. More motor bearings fail from churning excess grease than from "
                "starvation. If the relief port does not purge, stop and raise a work request rather than "
                "forcing additional grease.",
                "For two pump sets with one unit on standby, coordinate with operations to capture the "
                "standby unit during its scheduled exercise run, so that both units of the set carry "
                "current readings.",
                "Check oil-lubricated pump bearing housings at the sight glass, top up to the centre mark "
                "if required, and record any housing that needed more than a token top-up as a potential "
                "leak for follow-up.",
                "Report any machine with repeated elevated readings on the same measurement point over "
                "consecutive months to the reliability engineer for root cause investigation. Repeated "
                "symptoms with no root cause action is how chronic failures are made.",
            ]),
            ("Acceptance Criteria", [
                "The route is complete when every machine on the list has a full set of readings recorded, "
                "every zone C or D finding has a work request raised with the reading attached, and the "
                "lubrication tasks due in the month are signed off in the schedule.",
            ]),
            ("Records", [
                "Route readings are retained in the vibration database against each machine tag. Work "
                "requests raised from the route shall quote the reading, the zone, and the trend over the "
                "previous three months so that maintenance can prioritise on evidence. The route summary "
                "and the list of machines in zone C or above shall be tabled at the monthly reliability "
                "meeting, each with its open work order number.",
            ]),
        ],
    },
    {
        "sop_id": "SOP-114",
        "title": "Centrifugal Pump Suction Strainer Maintenance",
        "revision": "Rev 3",
        "rev_date": "14/08/2024",
        "applies_to": ["P-101A", "P-101B", "P-101C"],
        "sections": [
            ("Purpose", [
                "This procedure defines the method and the interval for inspecting and cleaning the "
                "temporary conical and permanent basket suction strainers fitted to the centrifugal "
                "process transfer pumps at Plant Site A. A plugged suction strainer starves the pump, "
                "causes cavitation and low discharge pressure trips, and is a leading cause of avoidable "
                "corrective work orders on the pump fleet.",
            ]),
            ("Scope", [
                "Applies to the suction strainers fitted to the P-101 series process transfer pumps, "
                "namely Pump 101A, Pump 101B and Pump 101C, and to the basket strainers on the utilities "
                "cooling water pumps. The procedure covers routine cleaning, inspection of the strainer "
                "element, and the differential pressure surveillance that triggers unscheduled cleaning.",
            ]),
            ("References", [
                "SOP-118 Equipment Isolation and Lock-Out Tag-Out.",
                "SOP-101 Centrifugal Pump Startup and Shutdown Procedure.",
                "Strainer manufacturer drawing showing element mesh size and gasket details.",
            ]),
            ("Safety Precautions", [
                "The pump shall be stopped, and the strainer housing isolated, drained and depressurised "
                "per SOP-118 before the cover is unbolted. Strainer housings hold trapped pressure; crack "
                "the vent before the final fasteners.",
                "Debris removed from strainers may include sharp metal fragments and process residue. "
                "Handle elements with cut-resistant gloves and dispose of debris to the designated bin.",
                "Where the standby pump is placed in service to allow cleaning, complete the changeover "
                "per SOP-101 before isolating the pump to be worked.",
            ]),
            ("Tools and Materials", [
                "Have available: strainer housing cover spanners, a new gasket of the specified material "
                "and size for the housing joint, cut resistant gloves, a soft bristle brush and low "
                "pressure wash water, a replacement strainer element from stores for exchange, a camera or "
                "work tablet for as-found photographs, a debris bin, and the work order for the pump tag.",
                "Verify the pump tag against the work order at the machine. The three units of the P-101 "
                "set are identical in the field, and cleaning the wrong strainer leaves the fouled unit in "
                "service with a clean paper record.",
            ]),
            ("Procedure", [
                "Confirm which pump of the set is to be worked and complete the changeover to the standby "
                "pump per SOP-101, verifying stable duty on the standby before isolating.",
                "Isolate, drain and vent the strainer housing per SOP-118. Verify zero pressure at the "
                "vent before removing the cover fasteners.",
                "Remove the cover and withdraw the strainer element. Photograph the as-found condition "
                "before any cleaning; the debris type and quantity is the primary record for interval "
                "review.",
                "Estimate and record the percentage blockage of the element open area. Note the debris "
                "character: silt, scale flakes, gasket fragments, vegetation or polymer lumps each point "
                "to a different upstream source.",
                "Compare the differential pressure history since the last cleaning against the 0.35 bar "
                "action limit, and note on the work order whether the limit was reached before the "
                "scheduled date. Early limit hits are the trigger for cleaning interval review.",
                "Wash the element with low pressure water and a soft brush. Do not use wire brushes or "
                "high pressure jetting on fine mesh elements, as mesh distortion passes debris to the "
                "pump it is meant to protect.",
                "Inspect the element for tears, distortion and corrosion. Hold the element against the "
                "light; any visible tear or opened mesh requires element replacement, not repair.",
                "Where the debris volume is unusually high or the debris character has changed, inspect "
                "the suction line and the tank outlet screen for the source before returning the pump to "
                "duty, and report the finding to the shift supervisor.",
                "Inspect the housing gasket face, fit a new gasket of the specified material, refit the "
                "element the correct way round per the flow arrow, and torque the cover fasteners evenly.",
                "Return the strainer to service, venting the housing as it fills, and check for leakage "
                "at the cover joint at operating pressure.",
                "Record the differential pressure across the strainer with the pump at normal duty. This "
                "reading is the clean baseline for surveillance until the next cleaning.",
            ]),
            ("Cleaning Interval", [
                "Strainer elements on the P-101 series transfer pumps shall be removed, inspected and "
                "cleaned at monthly intervals. The monthly interval applies year round and is the basis "
                "of the preventive maintenance schedule for these pumps.",
                "In addition to the scheduled monthly cleaning, an unscheduled cleaning shall be "
                "performed whenever the strainer differential pressure exceeds 0.35 bar at normal flow, "
                "or whenever pump suction pressure is observed trending down at constant tank level.",
                "The cleaning interval shall not be extended without a documented review by the "
                "reliability engineer of the recorded blockage percentages over the preceding twelve "
                "months.",
            ]),
            ("Acceptance Criteria", [
                "The task is accepted when the element is confirmed intact, the housing is leak free at "
                "operating pressure, the post-cleaning differential pressure is recorded as the new "
                "baseline, and the work order carries the blockage estimate and debris description for "
                "trend analysis.",
            ]),
            ("Records", [
                "Record every cleaning, scheduled or unscheduled, as a work order against the pump tag "
                "with the blockage percentage and debris type. The reliability engineer reviews these "
                "records annually to confirm the cleaning interval remains appropriate. A rising blockage "
                "trend at a constant interval is the leading indicator that the interval requires "
                "revision.",
            ]),
        ],
    },
    {
        "sop_id": "SOP-116",
        "title": "Cooling Water System Operation - Utilities Area",
        "revision": "Rev 1",
        "rev_date": "03/10/2024",
        "applies_to": ["P-102A", "P-102B", "P-103A", "HX-202A", "CV-303A"],
        "sections": [
            ("Purpose", [
                "This procedure defines normal operation of the Utilities Area cooling water system at "
                "Plant Site A, including pump duty rotation, basin level control and chemical dosing "
                "surveillance. Stable cooling water supply protects every heat exchanger and machine "
                "cooler on site, and most process temperature excursions trace back to cooling water "
                "disturbances that were preventable. The procedure also defines the surveillance readings "
                "that feed the reliability programme for the Utilities Area rotating equipment.",
            ]),
            ("Scope", [
                "Applies to the cooling water circulation pumps P-102A and P-102B, the auxiliary pump "
                "P-103A, the cooling water return exchanger HX-202A, and the basin makeup control valve "
                "CV-303A. Cooling tower fan maintenance and chemical dosing pump calibration are covered "
                "by their own procedures.",
            ]),
            ("References", [
                "SOP-101 Centrifugal Pump Startup and Shutdown Procedure.",
                "SOP-110 Rotating Equipment Vibration Monitoring and Bearing Lubrication.",
                "Cooling water chemical treatment control sheet issued by the treatment contractor.",
            ]),
            ("Safety Precautions", [
                "Cooling tower basins and sumps are confined spaces when drained. Entry requires a "
                "confined space permit without exception.",
                "Chemical dosing lines carry corrosive biocide and inhibitor concentrates. Wear chemical "
                "splash PPE when working near dosing points, and know the location of the safety shower.",
                "Do not approach the fan deck while any fan is in automatic; fans may start without "
                "warning on temperature control.",
            ]),
            ("Tools and Materials", [
                "Have available on rounds: the shift log or work tablet, the contractor chemical test kit "
                "with in-date reagents, chemical splash PPE for dosing point checks, a torch for basin "
                "screen inspection, and the utilities log sheet. A duty pump changeover additionally "
                "requires the SOP-101 checklist and radio contact with the panel operator.",
                "Verify the test kit reagent expiry dates weekly. Residual readings taken with expired "
                "reagents have repeatedly caused false out-of-range reports and unnecessary contractor "
                "callouts.",
            ]),
            ("Procedure", [
                "Operate the system with one main circulation pump on duty and one on standby autostart. "
                "The duty selection shall alternate between P-102A and P-102B on the first day of each "
                "month to equalise running hours across the pair.",
                "Complete the changeover per SOP-101: start the incoming pump, confirm stable discharge "
                "pressure, then stop the outgoing pump. Never leave both pumps stopped with exchangers "
                "on load, however briefly.",
                "Record the running hours of P-102A and P-102B at each monthly changeover and reconcile "
                "them quarterly. A growing gap in hours means the rotation is being skipped and one "
                "machine is quietly accumulating all of the wear.",
                "Check supply header pressure and temperature each shift and record them in the shift "
                "log. A falling header pressure at constant pump speed indicates strainer or basin "
                "screen blockage and shall be investigated the same shift.",
                "Maintain the basin level within the marked band using CV-303A on automatic makeup. If "
                "the valve is passing or hunting, place makeup on manual bypass control and raise a work "
                "request for the valve. Track basin makeup volume alongside the level record; rising "
                "makeup at a constant basin level indicates a circuit leak to be located and reported.",
                "Verify the side-stream filter is in service and back-flushing on its timer. A "
                "side-stream filter left in bypass measurably accelerates fouling of HX-202A and of "
                "every user exchanger on the circuit.",
                "Record the cooling water supply and return temperatures across HX-202A daily. A rising "
                "approach temperature at constant duty is the earliest indication of exchanger fouling "
                "and shall be reported to the reliability engineer for cleaning assessment against "
                "SOP-105.",
                "Once per shift, listen at each running pump for changes in sound and check the seal "
                "area visually. Operators detect most developing pump problems days before the monthly "
                "instrument route does, and a verbal report is sufficient to trigger a check reading.",
                "Confirm chemical dosing pumps are stroking and day tank levels are consistent with the "
                "dosing rate. Record free chlorine and inhibitor residuals from the contractor test "
                "kit each day shift, and report out-of-range residuals to the treatment contractor.",
                "After any power interruption, verify that the duty pump restarted or the standby cut "
                "in, and re-establish chemical dosing, which does not restart automatically and is "
                "routinely forgotten.",
                "Blow down the basin to the effluent system when conductivity exceeds the limit on the "
                "treatment control sheet, and record the blowdown volume.",
                "During monsoon operation, inspect the basin screens daily and brief the incoming shift "
                "on screen condition at every handover. Wind-blown debris loads rise sharply in the wet "
                "season, screen blockage propagates directly to pump suction problems, and in heavy "
                "weather the day shift record is stale by night.",
                "Report any pump vibration, unusual noise or seal weep observed during rounds as a work "
                "request against the pump tag, quoting SOP-110 for the vibration assessment.",
            ]),
            ("Acceptance Criteria", [
                "The system is considered in normal order when one pump carries duty with the standby "
                "available in autostart, header pressure and basin level are inside their bands, "
                "chemical residuals are in range, and the HX-202A approach temperature shows no rising "
                "trend over the trailing week.",
            ]),
            ("Records", [
                "Shift readings are recorded in the shift log. Monthly duty rotation, residual test "
                "results and blowdown volumes are retained on the utilities log sheet and reviewed at "
                "the monthly reliability meeting. Any excursion of header pressure, basin level or "
                "chemical residuals outside its control band shall be recorded together with the "
                "corrective action taken.",
            ]),
        ],
    },
    {
        "sop_id": "SOP-118",
        "title": "Equipment Isolation and Lock-Out Tag-Out",
        "revision": "Rev 6",
        "rev_date": "30/04/2025",
        "applies_to": ["P-101A", "P-101B", "P-101C", "P-102A", "P-102B", "P-103A",
                       "HX-201A", "HX-201B", "HX-202A", "CV-301A", "CV-302A", "CV-303A"],
        "sections": [
            ("Purpose", [
                "This procedure defines the mandatory method for isolating plant equipment from all "
                "energy sources before intrusive work, and for locking and tagging those isolations so "
                "they cannot be defeated while people are exposed. Isolation discipline is the single "
                "most important barrier against fatal accidents during maintenance at Plant Site A.",
            ]),
            ("Scope", [
                "Applies to every intrusive maintenance, inspection or cleaning task on registered "
                "equipment, including pumps, heat exchangers, control valves and their associated "
                "piping. It covers electrical, process, hydraulic and stored mechanical energy. Work on "
                "live electrical equipment is prohibited and is not enabled by this procedure.",
            ]),
            ("References", [
                "Site isolation standard and the plant single line diagrams.",
                "Piping and instrument diagrams for the system containing the equipment.",
                "Permit to work procedure for Plant Site A.",
            ]),
            ("Safety Precautions", [
                "Only authorised isolators listed on the site register may apply or remove isolations. "
                "Training does not confer authorisation; the register does.",
                "Every person working under an isolation shall fit their personal lock to the lockbox. "
                "No lock, no work, without exception.",
                "An isolation proven dead at the start of work is proven for that moment only. If the "
                "job is suspended overnight or the scope changes, the isolation shall be re-proven "
                "before work resumes.",
                "Never assume a valve position from its handwheel or lever. Verify by system response, "
                "vent behaviour or physical disconnection, because valve position indicators fail and "
                "gearbox drives strip without external sign.",
            ]),
            ("Tools and Materials", [
                "Have available: the site padlock series with unique keys, the lockbox, isolation tags "
                "and certificate forms, chains and valve covers for locked closed valves, rated blanking "
                "spades and bleed rings where positive isolation is specified, a voltage tester proved "
                "against a known live source for electrical proving, and the piping and instrument "
                "diagrams marked with the isolation points.",
                "Personal locks are individually issued and shall never be shared, transferred or "
                "removed by anyone other than the owner, except under the site lost-lock procedure "
                "administered by the safety department.",
            ]),
            ("Procedure", [
                "Plan the isolation on the piping and instrument diagram before going to the field. "
                "List every energy source: driver electrical supply, process connections, flushing "
                "connections, instrument air to actuated valves, and any stored energy such as sprung "
                "actuators or elevated liquid legs.",
                "Prepare the isolation certificate listing each isolation point with its unique valve or "
                "breaker identifier, the required state, and the securing method, whether lock, chain "
                "or blank.",
                "Isolate the driver electrically by racking out the breaker or withdrawing the fuses, "
                "and lock the switching device in the isolated position. Pressing the local start "
                "button is part of proving, never a substitute for electrical isolation.",
                "Isolate process connections by closing the identified valves and locking them closed. "
                "For entry into equipment or hot work, positive isolation by spade or physical "
                "disconnection is required; a closed valve alone is not positive isolation.",
                "Treat instrument air to spring return actuators, elevated liquid legs, accumulators "
                "and trapped thermal expansion as energy sources in their own right: isolate, vent or "
                "drain them on the certificate, and physically restrain any actuator that could move "
                "when air is removed.",
                "Drain and vent the equipment to the safe location identified on the certificate, and "
                "leave drains and vents open and tagged for the duration of the work.",
                "Prove dead at the point of work: attempt a local start for electrical isolation, and "
                "verify zero pressure at the equipment vent for process isolation, in the presence of "
                "the person doing the work.",
                "Fit the isolation tags at every point, place the isolation keys in the lockbox, and "
                "have every member of the working party fit a personal lock before first tool contact.",
                "Where two or more work parties share an isolation, each party fits its own lock to the "
                "common lockbox, and the isolation shall not be broken until every party has signed off "
                "and removed its lock. The isolator owns the count.",
                "Long term isolations spanning more than one shift shall be revalidated at each shift "
                "handover by the oncoming authorised isolator, walking the points against the "
                "certificate and initialling the validation record.",
                "On completion, the isolator shall walk the isolation list in reverse, confirming the "
                "work site is clear, guards are refitted and every person has removed their lock, "
                "before restoring any energy source.",
                "Return the equipment to the operating team formally, and file the completed isolation "
                "certificate against the work order for the equipment tag.",
            ]),
            ("Acceptance Criteria", [
                "An isolation is acceptable only when every energy source on the certificate is "
                "isolated, secured and proven dead at the point of work, and every worker is protected "
                "by a personal lock. Restoration is complete only when the certificate is signed off "
                "and the operating team has accepted the equipment back.",
            ]),
            ("Records", [
                "Completed isolation certificates are retained with the associated work order for two "
                "years. Any isolation defeated, missing or found in the wrong state shall be reported "
                "as a high potential incident and investigated. The site isolation register shall be "
                "audited quarterly by the safety department, sampling live isolations in the field "
                "against their certificates.",
            ]),
        ],
    },
]
