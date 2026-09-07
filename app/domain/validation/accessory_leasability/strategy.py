from app.shared.decision_strategies.nodes import (
    CriterionNode,
    DecisionNode,
    DecisionStrategy,
    StrategyDecision,
)


def standard_leasability_strategy() -> DecisionStrategy:
    return DecisionStrategy(
        id="standard_accessory_leasability",
        version="0.1.0",
        entry_node_id="explicitly_not_leasable_type_check",
        nodes={
            "explicitly_not_leasable_type_check": CriterionNode(
                "explicitly_not_leasable_type_check",
                "explicitly_not_leasable_type",
                "not_leasable_type_special_rules_check",
                "explicitly_leasable_type_check",
                "explicitly_leasable_type_check",
            ),
            "not_leasable_type_special_rules_check": CriterionNode(
                "not_leasable_type_special_rules_check",
                "special_rules",
                "leasable",
                "not_leasable",
                "not_leasable",
            ),
            "explicitly_leasable_type_check": CriterionNode(
                "explicitly_leasable_type_check",
                "explicitly_leasable_type",
                "leasable_type_special_rules_check",
                "technical_bicycle_component_check",
                "technical_bicycle_component_check",
            ),
            "leasable_type_special_rules_check": CriterionNode(
                "leasable_type_special_rules_check",
                "special_rules",
                "leasable",
                "not_leasable",
                "leasable",
            ),
            "technical_bicycle_component_check": CriterionNode(
                "technical_bicycle_component_check",
                "technical_bicycle_component",
                "leasable",
                "stvzo_equipment_check",
                "stvzo_equipment_check",
            ),
            "stvzo_equipment_check": CriterionNode(
                "stvzo_equipment_check",
                "stvzo_equipment",
                "leasable",
                "functional_unit_check",
                "functional_unit_check",
            ),
            "functional_unit_check": CriterionNode(
                "functional_unit_check",
                "functional_unit_with_bicycle",
                "leasable",
                "installable_on_bicycle_check",
                "installable_on_bicycle_check",
            ),
            "installable_on_bicycle_check": CriterionNode(
                "installable_on_bicycle_check",
                "installable_on_bicycle",
                "leasable",
                "not_leasable",
                "not_leasable",
            ),
            "leasable": DecisionNode(
                "leasable",
                StrategyDecision.ACCEPT,
                "ACCESSORY_LEASABLE",
                "El accesorio es financiable.",
            ),
            "not_leasable": DecisionNode(
                "not_leasable",
                StrategyDecision.REJECT,
                "ACCESSORY_NOT_LEASABLE",
                "El accesorio no es financiable.",
            ),
        },
    )
