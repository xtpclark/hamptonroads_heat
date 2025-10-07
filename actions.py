from sqlalchemy import text
from db import engine
import random

def handle_sweep_action(locality):
    """Aggressive enforcement targeting shootings. CONSUMES 15 police force."""
    with engine.connect() as conn:
        # Check current police force
        police_force = conn.execute(text(
            "SELECT police_force FROM sim_states ORDER BY id DESC LIMIT 1"
        )).scalar() or 100
        
        if police_force < 15:
            return {
                'success': False,
                'message': f"Insufficient police force ({police_force:.1f}/100). Officers exhausted from recent operations. Cannot execute sweep.",
                'incidents_affected': 0,
                'police_force_cost': 0
            }
        
        count_query = text("""
            SELECT COUNT(*) FROM incidents 
            WHERE type = 'shooting' AND locality = :loc AND weight > 1
        """)
        total_shootings = conn.execute(count_query, {'loc': locality}).scalar()
        
        if total_shootings == 0:
            return {
                'success': False,
                'message': f"No active shooting incidents found in {locality}. Resources wasted. (-5 police force)",
                'incidents_affected': 0,
                'police_force_cost': 5
            }
        
        update_query = text("""
            UPDATE incidents SET weight = weight * 0.5 
            WHERE id IN (
                SELECT id FROM incidents 
                WHERE type = 'shooting' AND locality = :loc 
                ORDER BY random() 
                LIMIT GREATEST(1, (SELECT CAST(COUNT(*) * 0.2 AS INTEGER) FROM incidents WHERE type = 'shooting' AND locality = :loc))
            )
        """)
        result = conn.execute(update_query, {'loc': locality})
        conn.commit()
        
        return {
            'success': True,
            'message': f"Enforcement sweep: {result.rowcount} of {total_shootings} shooting hotspots suppressed. Heavy-handed tactics drew criticism. (-15 police force)",
            'incidents_affected': result.rowcount,
            'total_count': total_shootings,
            'police_force_cost': 15
        }

def handle_increase_patrols_action(locality):
    """Visible police presence reducing opportunistic crime. CONSUMES 8 police force."""
    with engine.connect() as conn:
        police_force = conn.execute(text(
            "SELECT police_force FROM sim_states ORDER BY id DESC LIMIT 1"
        )).scalar() or 100
        
        if police_force < 8:
            return {
                'success': False,
                'message': f"Insufficient police force ({police_force:.1f}/100). Cannot increase patrols.",
                'incidents_affected': 0,
                'police_force_cost': 0
            }
        
        count_query = text("""
            SELECT COUNT(*) FROM incidents 
            WHERE type IN ('petty_theft', 'vandalism', 'larceny_auto') AND locality = :loc
        """)
        total_crimes = conn.execute(count_query, {'loc': locality}).scalar()
        
        update_query = text("""
            UPDATE incidents 
            SET weight = GREATEST(1, CAST(weight * 0.75 AS INTEGER)) 
            WHERE type IN ('petty_theft', 'vandalism', 'larceny_auto') AND locality = :loc
        """)
        result = conn.execute(update_query, {'loc': locality})
        conn.commit()
        
        return {
            'success': True,
            'message': f"Increased patrols reduced {result.rowcount} opportunistic crimes out of {total_crimes} total. (-8 police force)",
            'incidents_affected': result.rowcount,
            'police_force_cost': 8
        }

def handle_task_force_action(locality):
    """Specialized unit targeting the most prevalent crime. CONSUMES 20 police force."""
    with engine.connect() as conn:
        police_force = conn.execute(text(
            "SELECT police_force FROM sim_states ORDER BY id DESC LIMIT 1"
        )).scalar() or 100
        
        if police_force < 20:
            return {
                'success': False,
                'message': f"Insufficient police force ({police_force:.1f}/100). Cannot form specialized task force.",
                'incidents_affected': 0,
                'police_force_cost': 0
            }
        
        crime_query = text("""
            SELECT type, COUNT(*) as cnt, SUM(weight) as total_weight
            FROM incidents 
            WHERE locality = :loc AND weight > 2
            GROUP BY type 
            ORDER BY total_weight DESC 
            LIMIT 1
        """)
        top_crime = conn.execute(crime_query, {'loc': locality}).fetchone()
        
        if not top_crime or top_crime[1] == 0:
            return {
                'success': False,
                'message': f"No significant crime patterns found to justify a task force. Budget wasted. (-5 police force)",
                'incidents_affected': 0,
                'police_force_cost': 5
            }
        
        crime_type, count, weight = top_crime
        
        update_query = text("""
            UPDATE incidents 
            SET weight = GREATEST(1, CAST(weight * 0.3 AS INTEGER))
            WHERE type = :crime_type AND locality = :loc
        """)
        result = conn.execute(update_query, {'crime_type': crime_type, 'loc': locality})
        conn.commit()
        
        crime_display = crime_type.replace('_', ' ').title()
        
        return {
            'success': True,
            'message': f"Task force crackdown on {crime_display}: {result.rowcount} incidents heavily suppressed. Civil liberties groups alarmed. (-20 police force)",
            'incidents_affected': result.rowcount,
            'crime_type': crime_display,
            'police_force_cost': 20
        }

def handle_technology_action(locality):
    """Surveillance technology reducing property crimes."""
    with engine.connect() as conn:
        query = text("""
            UPDATE incidents 
            SET weight = GREATEST(1, CAST(weight * 0.55 AS INTEGER))
            WHERE type IN ('petty_theft', 'larceny_auto', 'vandalism', 'robbery') 
            AND locality = :loc
        """)
        result = conn.execute(query, {'loc': locality})
        conn.commit()
        
        return {
            'success': True,
            'message': f"Surveillance network deployed. {result.rowcount} property crime hotspots now monitored. Privacy advocates protesting.",
            'incidents_affected': result.rowcount
        }

def handle_community_policing_action(locality):
    """Officers build relationships, slow crime reduction across all types. RESTORES 5 police force."""
    with engine.connect() as conn:
        query = text("""
            UPDATE incidents 
            SET weight = GREATEST(1, CAST(weight * 0.90 AS INTEGER))
            WHERE locality = :loc
        """)
        result = conn.execute(query, {'loc': locality})
        conn.commit()
        
        return {
            'success': True,
            'message': f"Community policing program launched. Officers walking beats and engaging residents. {result.rowcount} incidents showing marginal improvement. (+5 police force - officers less stressed)",
            'incidents_affected': result.rowcount,
            'police_force_cost': -5  # Negative cost = restoration
        }

def handle_crisis_training_action(locality):
    """De-escalation training preventing violent encounters."""
    with engine.connect() as conn:
        query = text("""
            UPDATE incidents 
            SET weight = GREATEST(1, CAST(weight * 0.65 AS INTEGER))
            WHERE type IN ('assault', 'shooting') 
            AND locality = :loc
        """)
        result = conn.execute(query, {'loc': locality})
        conn.commit()
        
        return {
            'success': True,
            'message': f"Crisis intervention training completed. {result.rowcount} violent confrontations de-escalated through improved tactics.",
            'incidents_affected': result.rowcount
        }

def handle_aid_action(locality):
    """Social services addressing root causes - slow, minor impact."""
    with engine.connect() as conn:
        query = text("""
            UPDATE incidents 
            SET weight = GREATEST(1, CAST(weight * 0.93 AS INTEGER)) 
            WHERE type IN ('petty_theft', 'od') 
            AND locality = :loc
        """)
        result = conn.execute(query, {'loc': locality})
        conn.commit()
        
        return {
            'success': True,
            'message': f"Social services expanded: addiction treatment, housing assistance. {result.rowcount} individuals receiving support. Long-term investment.",
            'incidents_affected': result.rowcount
        }

def handle_youth_programs_action(locality):
    """After-school programs and mentoring with delayed benefits."""
    with engine.connect() as conn:
        query = text("""
            UPDATE incidents 
            SET weight = GREATEST(1, CAST(weight * 0.96 AS INTEGER))
            WHERE type IN ('petty_theft', 'vandalism') 
            AND locality = :loc
        """)
        result = conn.execute(query, {'loc': locality})
        conn.commit()
        
        return {
            'success': True,
            'message': f"Youth intervention programs launched. {result.rowcount} minor crimes prevented. Benefits compound over time.",
            'incidents_affected': result.rowcount
        }

def handle_business_incentives_action(locality):
    """Economic development reducing crime through job creation."""
    with engine.connect() as conn:
        # Check crime levels to determine effectiveness
        crime_check = text("""
            SELECT COUNT(*) FROM incidents 
            WHERE locality = :loc AND weight > 5
        """)
        high_crime_areas = conn.execute(crime_check, {'loc': locality}).scalar()
        
        if high_crime_areas > 30:
            return {
                'success': False,
                'message': f"Business incentives failed. Crime too high ({high_crime_areas} hotspots) - no businesses interested. Budget wasted.",
                'incidents_affected': 0
            }
        
        # Reduce economic crimes
        query = text("""
            UPDATE incidents 
            SET weight = GREATEST(1, CAST(weight * 0.85 AS INTEGER))
            WHERE type IN ('petty_theft', 'robbery', 'larceny_auto') 
            AND locality = :loc
        """)
        result = conn.execute(query, {'loc': locality})
        conn.commit()
        
        return {
            'success': True,
            'message': f"Business development package attracting investment. {result.rowcount} economic crimes reduced through job creation.",
            'incidents_affected': result.rowcount
        }

def handle_infrastructure_action(locality):
    """Visible improvements to blighted areas."""
    with engine.connect() as conn:
        query = text("""
            UPDATE incidents 
            SET weight = GREATEST(1, CAST(weight * 0.88 AS INTEGER))
            WHERE type IN ('vandalism', 'petty_theft') 
            AND locality = :loc
        """)
        result = conn.execute(query, {'loc': locality})
        conn.commit()
        
        return {
            'success': True,
            'message': f"Infrastructure improvements: repaved streets, new lighting, cleaned vacant lots. {result.rowcount} incidents reduced. Community morale boosted.",
            'incidents_affected': result.rowcount
        }

def handle_transparency_action(locality):
    """Publish crime stats - backfires if crime is high."""
    with engine.connect() as conn:
        crime_count = conn.execute(
            text("SELECT COUNT(*) FROM incidents WHERE locality = :loc AND weight > 3"),
            {'loc': locality}
        ).scalar()
        
        serious_crimes = conn.execute(
            text("SELECT COUNT(*) FROM incidents WHERE locality = :loc AND type IN ('shooting', 'homicide', 'assault') AND weight > 5"),
            {'loc': locality}
        ).scalar()
        
        if crime_count > 50 or serious_crimes > 15:
            return {
                'success': False,
                'message': f"Transparency backfired! Report revealed {crime_count} active incidents including {serious_crimes} violent crimes. Media firestorm.",
                'incidents_affected': crime_count,
                'reputation_override': -12,
                'backlash_override': 10
            }
        else:
            return {
                'success': True,
                'message': f"Crime statistics published showing {crime_count} incidents, {serious_crimes} violent. Public appreciates transparency.",
                'incidents_affected': crime_count
            }

def handle_accountability_action(locality):
    """Civilian oversight board - pure trust-building."""
    with engine.connect() as conn:
        # No crime reduction, but check for recent controversial incidents
        shooting_check = text("""
            SELECT COUNT(*) FROM incidents 
            WHERE type = 'shooting' AND locality = :loc 
            AND timestamp > NOW() - INTERVAL '7 days'
        """)
        recent_shootings = conn.execute(shooting_check, {'loc': locality}).scalar()
        
        if recent_shootings > 5:
            return {
                'success': True,
                'message': f"Civilian review board established. Immediate scrutiny of {recent_shootings} recent shooting incidents. Community trust improving.",
                'incidents_affected': 0,
                'reputation_override': 20  # Bonus if timely
            }
        else:
            return {
                'success': True,
                'message': f"Independent oversight board created. No immediate crime impact but accountability measures in place.",
                'incidents_affected': 0
            }

def handle_no_action(locality):
    """Budget conservation - problems persist."""
    with engine.connect() as conn:
        crime_count = conn.execute(
            text("SELECT COUNT(*) FROM incidents WHERE locality = :loc AND weight > 3"),
            {'loc': locality}
        ).scalar()
        
        return {
            'success': True,
            'message': f"No action taken. Budget conserved but {crime_count} active incidents remain unaddressed. Status quo maintained.",
            'incidents_affected': 0
        }

def handle_traffic_action(locality):
    """Traffic enforcement campaign."""
    with engine.connect() as conn:
        query = text("""
            UPDATE incidents 
            SET weight = GREATEST(1, CAST(weight * 0.70 AS INTEGER))
            WHERE type = 'traffic' AND locality = :loc
        """)
        result = conn.execute(query, {'loc': locality})
        conn.commit()
        
        return {
            'success': True,
            'message': f"Traffic enforcement reduced {result.rowcount} traffic incidents through safety checkpoints and education.",
            'incidents_affected': result.rowcount
        }
