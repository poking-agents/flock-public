"""State type definitions for workflows"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from type_defs.base import Node, Option
from type_defs.operations import MiddlemanSettings, OperationResult


class BaseState(BaseModel):
    id: str = Field('', description='State ID, used as a filename')
    pass


DEFAULT_TIMEOUT = 60


class AgentState(BaseState):
    previous_results: List[List[OperationResult]] = Field(default_factory=list)
    task_string: str = Field('', description='Task description')
    nodes: List[Node] = Field(default_factory=list)
    timeout: int = Field(DEFAULT_TIMEOUT, description=
        'Command timeout in seconds')
    token_limit: int = Field(300000, description='Maximum tokens allowed')
    token_usage: int = Field(0, description='Current token usage')
    time_limit: float = Field(604800.0, description=
        'Maximum time allowed in seconds')
    time_usage: float = Field(0.0, description='Current time usage in seconds')
    actions_limit: int = Field(1000, description='Maximum actions allowed')
    actions_usage: int = Field(0, description='Current actions usage')
    scoring: Dict[str, Any] = Field(default_factory=dict, description=
        'Task scoring configuration')
    output_limit: int = Field(10000, description=
        'Maximum output length included in agent requests')
    context_trimming_threshold: int = Field(500000, description=
        'Character threshold for context trimming')
    last_rating_options: Optional[List[Option]] = None


class triframeSettings(BaseModel):
    advisors: List[MiddlemanSettings] = Field(default_factory=lambda : [
        MiddlemanSettings()], description='List of advisor model settings')
    actors: List[MiddlemanSettings] = Field(default_factory=lambda : [
        MiddlemanSettings()], description='List of actor model settings')
    raters: List[MiddlemanSettings] = Field(default_factory=lambda : [
        MiddlemanSettings()], description='List of rater model settings')
    limit_type: str = Field('token', description='Type of usage limit')
    intermediate_scoring: bool = Field(False, description=
        'Enable intermediate scoring')
    require_function_call: bool = Field(False, description=
        'Require function calls')
    enable_advising: bool = Field(True, description='Enable advisor phase')
    enable_subagents: bool = Field(False, description=
        'Enable subagent launching')


class TournamentMatch(BaseModel):
    """A single match between two agents"""
    agents: List[str]
    winner_id: Optional[str] = None
    reasoning: Optional[str] = None
    task: str
    timestamp: str = Field(default_factory=lambda : datetime.now().isoformat())


class TournamentRound(BaseModel):
    """A round of tournament matches"""
    matches: List[TournamentMatch]
    round_number: int
    timestamp: str = Field(default_factory=lambda : datetime.now().isoformat())


class Tournament(BaseModel):
    """A complete tournament"""
    id: str = Field(default_factory=lambda :
        f"tournament_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    initial_agents: List[str]
    rounds: List[TournamentRound] = Field(default_factory=list)
    status: str = 'in_progress'
    winner_id: Optional[str] = None
    task: str
    agent_conclusions: Dict[str, str] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda : datetime.now().isoformat())


class triframeState(AgentState):
    settings: triframeSettings = Field(default_factory=triframeSettings)
    active_subagents: List[Dict[str, Any]] = Field(default_factory=list)
    subagent_config: Optional[Dict[str, Any]] = Field(default=None)
    status: str = Field('initialized', description=
        'State status (for subagents)')
    tournaments: List[Tournament] = Field(default_factory=list)

    def is_subagent(self) ->bool:
        """Check if this state represents a subagent"""
        return self.subagent_config is not None

    def add_subagent(self, agent_id: str, task: str, approach: str,
        include_task_description: bool) ->None:
        """Add a subagent to active agents"""
        self.active_subagents.append({'id': agent_id, 'task': task,
            'approach': approach, 'include_task_description':
            include_task_description, 'status': 'initialized'})

    def start_new_tournament(self, agent_ids: List[str]) ->None:
        """Start a new tournament with the given agents"""
        tournament = Tournament(initial_agents=agent_ids)
        self.tournaments.append(tournament)

    def start_new_tournament(self, agent_ids: List[str], task: Optional[str
        ]=None) ->Tournament:
        """Start a new tournament with the given agents"""
        if task is None and agent_ids:
            agent = next((a for a in self.active_subagents if a['id'] ==
                agent_ids[0]), None)
            if agent:
                task = agent.get('task', 'Unknown task')
            else:
                task = 'Unknown task'
        tournament = Tournament(initial_agents=agent_ids, task=task)
        self.tournaments.append(tournament)
        return tournament

    def get_active_agents_for_round(self, tournament: Tournament) ->List[str]:
        """Get the list of agents still active in the tournament"""
        if not tournament.rounds:
            return tournament.initial_agents
        last_round = tournament.rounds[-1]
        winners = [m.winner_id for m in last_round.matches if m.winner_id
             is not None]
        return winners

    def add_tournament_round(self, tournament: Tournament, matches: List[
        TournamentMatch]) ->None:
        """Add a new round to the tournament"""
        round_number = len(tournament.rounds) + 1
        tournament.rounds.append(TournamentRound(matches=matches,
            round_number=round_number))

    def complete_tournament(self, tournament: Tournament, winner_id: str
        ) ->None:
        """Mark a tournament as completed with a winner"""
        tournament.status = 'completed'
        tournament.winner_id = winner_id

    def get_current_tournament(self) ->Optional[Tournament]:
        """Get the current active tournament"""
        return next((t for t in self.tournaments if t.status ==
            'in_progress'), None)

    def update_usage(self):
        """Update usage statistics from latest results"""
        latest_results = self.previous_results[-1]
        usage_result = next((r for r in latest_results if r.type ==
            'get_usage'), None)
        if usage_result:
            usage = usage_result.result.usage
            self.token_usage = usage.tokens
            self.actions_usage = usage.actions
            self.time_usage = usage.total_seconds
            if self.nodes:
                self.nodes[-1].token_usage = usage.tokens
                self.nodes[-1].actions_usage = usage.actions
                self.nodes[-1].time_usage = usage.total_seconds
        elif self.nodes:
            self.nodes[-1].token_usage = self.token_usage
            self.nodes[-1].actions_usage = self.actions_usage
            self.nodes[-1].time_usage = self.time_usage
