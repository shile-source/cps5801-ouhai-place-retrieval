"""Separate unjudged rater slot on an existing packet; never copies judgments."""
import json
import random
from pathlib import Path
from .human_pilot import Pilot, now, sha

ROOT=Path(__file__).resolve().parents[2]
REFERENCE=ROOT/'data/labels/pilot_human_v0_1_20261102'
SESSION=ROOT/'data/labels/supplemental_rater_b_v1_20261125'
SAMPLED_SESSION=ROOT/'data/labels/supplemental_rater_b_sample80_v1_20261125'


def prepare_second_rater(reference=REFERENCE,session=SESSION,*,sample_per_query=None):
    reference,session=Path(reference),Path(session)
    original=Pilot(reference)
    original.verify()
    if session.exists():
        current=Pilot(session)
        if current.packet.get('reference_packet_sha256')!=original.manifest['packet_sha256']:
            raise ValueError('Existing second-rater packet belongs to different inputs')
        if current.packet.get('sample_per_query')!=sample_per_query:
            raise ValueError('Existing packet has a different sampling plan; never overwrite it')
        return session
    packet=dict(original.packet)
    packet.update(purpose='supplemental_second_rater_same_AI_assisted_pilot_queries',
                  created_at=now(),human_reviewed=False,formal_evaluation=False,
                  rater_slot='B',annotator_prior_exposure=None,
                  independent_authorship=False,independent_ratings_verified=False,
                  reference_packet_sha256=original.manifest['packet_sha256'],
                  reference_action_log_sha256=sha(reference/'human_actions.jsonl') if (reference/'human_actions.jsonl').exists() else None,
                  field_evidence_base='data/clean/pilot_mixed_v0_3_osm_20261031/field_evidence.json',
                  query_design='Same existing AI-assisted eight-query convenience Pilot; not the new submitted twelve drafts')
    packet['rules']=('仅评价来源快照文字，不推断地点当前营业、安静程度或实际区属。'
        '2=核心需求有充分事实支持；1=有事实支持部分需求；0=有事实可判断不相关。'
        '资料不足请说明缺少事实，不填0。只勾选实际使用的证据。'
        '座位较多约定为>=40，藏书较多约定为>=12000；仅适用于对应查询。'
        '请自己判断，不查看另一位评分者的分数或模型排名，不让AI代评分。'
        '查询是AI辅助的既有Pilot；本页独立保存第二份判断，不宣称新的独立测试集。')
    if sample_per_query is not None:
        if type(sample_per_query) is not int or not 1<=sample_per_query<=len(packet['candidate_ids']):
            raise ValueError('Invalid number of sampled candidates per query')
        packet.update(sample_per_query=sample_per_query,sampling_seed=5801,
                      sampling_method='uniform_without_replacement_per_query_sorted_ids_seed_string_5801:query_id',
                      selection_uses_model_rankings_or_grades=False,
                      purpose='supplemental_stratified_pair_sample_second_rater_NOT_full_dual_annotation')
        packet['sampled_tasks']=[
            [q['query_id'],pid] for q in packet['queries']
            for pid in random.Random('5801:'+q['query_id']).sample(sorted(packet['candidate_ids']),sample_per_query)]
    session.mkdir(parents=True,exist_ok=False)
    (session/'corpus.json').write_bytes((reference/'corpus.json').read_bytes())
    (session/'packet.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest={'packet_sha256':sha(session/'packet.json'),'corpus_sha256':sha(session/'corpus.json')}
    (session/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return session


def make_page(*,total=392,sampled=False):
    template=(ROOT/'src/demo/annotation.html').read_text(encoding='utf-8')
    template=template.replace('CPS5801：人工相关性 Pilot','CPS5801：第二位评分者')
    start=template.index('<p class="notice">')
    end=template.index('</p>',start)+4
    introduction=(f'每个查询固定抽10个地点，共{total}对。完成这些即可，不用做392对。' if sampled else f'共{total}对。')
    template=template[:start]+('<p class="notice">这是第二位评分者的单独记录：49条来源候选、8个既有查询。'+introduction+
        '不显示第一位分数或模型排名；请亲自判断，不交流答案或让AI代评分。查询本身有AI辅助来源，'
        '这次是补充双人评价，不是新独立测试集。每次点击判断后自动保存，可以分次完成。</p>')+template[end:]
    template=template.replace('评分者英文署名','评分者代号（本页仅供第二位评分者使用）')
    template=template.replace('placeholder="例如 Shi Letian"','placeholder="填写你自己的代号"')
    template=template.replace("current.queries.findIndex(q=>q.query_id===$('querySelect').value)*current.candidate_count",
                              "current.query_task_starts[$('querySelect').value]")
    start=template.index('<section><h2>第三步：')
    end=template.index('</section>',start)+len('</section>')
    template=template[:start]+('<section><h2>完成后</h2><p>全部处理后告诉项目负责人。判断已逐条保存到D盘，'
        '不用另点提交。本页不会计算模型指标或展示另一人的结果。</p>'
        '<button id="evaluate" hidden disabled>本页不计算指标</button><div id="results"></div></section>')+template[end:]
    template=template.replace('if(remember)rememberPosition(data);return data;',
        "for(const b of document.querySelectorAll('[data-grade]'))b.disabled=!!data.ratings_locked;$('unknown').disabled=!!data.ratings_locked;if(data.ratings_locked)$('existing').textContent+='；本版已完成并锁定，不用再评分。';if(remember)rememberPosition(data);return data;")
    return template


class SecondRaterPilot(Pilot):
    def __init__(self,session=SESSION):
        super().__init__(session)
        if 'sampled_tasks' in self.packet:
            tasks=[tuple(pair) for pair in self.packet['sampled_tasks']]
            if not tasks or len(tasks)!=len(set(tasks)) or any(q not in self.queries or p not in self.records for q,p in tasks):
                raise ValueError('Invalid frozen sampled task list')
            for qid in self.queries:
                if sum(q==qid for q,p in tasks)!=self.packet['sample_per_query']:
                    raise ValueError('Sample allocation differs from frozen plan')
            self.tasks=tasks

    def rate(self,qid,pid,grade,reason='',evidence='',notes=''):
        with self.lock:
            if (self.path/'analysis_lock.json').exists():
                raise ValueError('本版评分已完成并用于一致性分析，已锁定；纠错请保留原版另建版本')
            if (qid,pid) not in self.tasks:
                raise ValueError('This pair is outside the frozen second-rater sample')
            return super().rate(qid,pid,grade,reason,evidence,notes)

    def state(self,index=0):
        value=super().state(index)
        value['rater_slot']='B'
        value['field_evidence_ref']=self.packet['field_evidence_base']+'#'+value['candidate']['poi_id']
        value['query_task_starts']={qid:next(i for i,pair in enumerate(self.tasks) if pair[0]==qid) for qid in self.queries}
        value['sampled_review']='sampled_tasks' in self.packet
        marker=self.path/'analysis_lock.json'
        value['ratings_locked']=marker.exists()
        if marker.exists():
            locked=json.loads(marker.read_text(encoding='utf-8'))
            if sha(self.path/'human_actions.jsonl')!=locked.get('actions_sha256'):
                raise ValueError('Locked second-rater action log changed; stop and preserve evidence')
        return value

    def evaluate(self,fetch=None):
        raise ValueError('Second-rater collection never calls a model or publishes metrics')
