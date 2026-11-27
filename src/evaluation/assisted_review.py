"""Human decisions after visible assistant-authored rule suggestions, never blind labels."""
from src.evaluation.adjudication import Adjudication


class AssistedReview(Adjudication):
    action = 'human_review_of_visible_ai_rule_suggestion'
    source = 'assisted_review_user_ui'
    role = 'ai_assisted_human_reviewer_not_independent'

    def decide(self, case_id, grade, reason, reviewer, confirmed):
        if self.packet['purpose'] != 'ai_assisted_development_review_NOT_independent_test':
            raise ValueError('Wrong assisted review packet')
        return super().decide(case_id, grade, reason, reviewer, confirmed)

    def state(self, index=0):
        state = super().state(index)
        state.update(suggestions_are_human_labels=False, requires_each_human_confirmation=True)
        return state

    def export(self):
        value = super().export()
        value.update(query_authorship=self.packet.get('query_authorship','AI_assistant'), suggestions_authorship='assistant_authored_explicit_rules',
                     independently_blind=False, human_confirmed_count=value['handled'])
        return value
