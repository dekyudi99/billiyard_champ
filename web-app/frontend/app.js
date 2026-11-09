const { createApp, ref, computed, onMounted } = Vue;

createApp({
    setup() {
        const currentTab = ref('road-to-world');
        const mobileMenuOpen = ref(false);
        const openSettingsModal = ref(false);

        const tabs = [
            { id: 'road-to-world', name: 'Road to World', shortName: 'Road to World', icon: '🌐' },
            { id: 'base-team', name: 'Base Team', shortName: 'Base Team', icon: '👥' },
            { id: 'base-region', name: 'Base Region', shortName: 'Base Region', icon: '🌍' },
            { id: 'workflow', name: 'Alur Season & Turnamen', shortName: 'Alur Season', icon: '🔄' },
            { id: 'trophies-history', name: 'Riwayat Trofi', shortName: 'Riwayat Trofi', icon: '🏆' },
            { id: 'tournaments', name: 'Turnamen & Bagan', shortName: 'Turnamen', icon: '📊' },
        ];

        // State data
        const stats = ref({});
        const teams = ref([]);
        const regions = ref([]);
        const tournaments = ref([]);
        const roadData = ref({ m_championship: { slots: [] }, msl_championship: { slots: [] } });
        const selectedTournamentData = ref(null);
        const trophiesHistory = ref([]);
        const selectedTeamForCabinet = ref(null);

        // Filters
        const selectedRegionFilter = ref('');
        const tournamentTypeFilter = ref('ALL');
        const selectedTrophySeasonFilter = ref('');
        const selectedSeasonWorkflow = ref(4);

        // Tournament Modal States
        const tournamentModalView = ref('bracket'); // 'bracket' | 'list'
        const tournamentModalStage = ref('PLAYOFF'); // 'PLAYOFF' | 'SWISS'
        const editingMatch = ref(null);
        const matchEditForm = ref({
            score1: 0,
            score2: 0,
            winner_id: '',
            status: 'COMPLETED'
        });

        // Finish Tournament Form
        const finishForm = ref({
            winner_id: '',
            runner_up_id: '',
            third_place_id: '',
            fourth_place_id: ''
        });

        // Workflow state
        const workflowData = ref({
            season: 4,
            current_phase: 1,
            phase_name: 'Fase 1: MPL Regional',
            all_mpl_done: false,
            mpl_completed_count: 6,
            msl_done: false,
            can_start_msl: false,
            m_done: false,
            can_start_m: false,
            can_start_next_season: false
        });

        // Settings Form
        const settingsForm = ref({
            msl_extra_slot_rule: 'defending_m_champ_region',
            msl_extra_team: 'DK'
        });

        const availableSeasons = computed(() => {
            const maxS = Math.max(stats.value?.active_season || 4, 4);
            return Array.from({ length: maxS }, (_, i) => i + 1);
        });

        // API Fetchers
        const fetchStats = async () => {
            try {
                const res = await fetch('/api/stats');
                stats.value = await res.json();
            } catch (e) {
                console.error("Error fetching stats:", e);
            }
        };

        const fetchTeams = async () => {
            try {
                const res = await fetch('/api/teams');
                teams.value = await res.json();
            } catch (e) {
                console.error("Error fetching teams:", e);
            }
        };

        const fetchRegions = async () => {
            try {
                const res = await fetch('/api/regions');
                regions.value = await res.json();
            } catch (e) {
                console.error("Error fetching regions:", e);
            }
        };

        const fetchTournaments = async () => {
            try {
                const res = await fetch('/api/tournaments');
                tournaments.value = await res.json();
            } catch (e) {
                console.error("Error fetching tournaments:", e);
            }
        };

        const fetchRoadToWorld = async () => {
            try {
                const res = await fetch('/api/road-to-world');
                roadData.value = await res.json();
                if (roadData.value.settings) {
                    settingsForm.value.msl_extra_slot_rule = roadData.value.settings.msl_extra_slot_rule || 'defending_m_champ_region';
                    settingsForm.value.msl_extra_team = roadData.value.settings.msl_extra_team || 'DK';
                }
            } catch (e) {
                console.error("Error fetching road to world:", e);
            }
        };

        const fetchTrophiesHistory = async () => {
            try {
                const res = await fetch('/api/trophies/history');
                trophiesHistory.value = await res.json();
            } catch (e) {
                console.error("Error fetching trophies history:", e);
            }
        };

        const fetchWorkflowStatus = async () => {
            try {
                const res = await fetch(`/api/season-workflow/${selectedSeasonWorkflow.value}`);
                if (res.ok) {
                    workflowData.value = await res.json();
                }
            } catch (e) {
                console.error("Error fetching workflow status:", e);
            }
        };

        const refreshAll = async () => {
            await Promise.all([
                fetchStats(),
                fetchTeams(),
                fetchRegions(),
                fetchTournaments(),
                fetchRoadToWorld(),
                fetchTrophiesHistory(),
                fetchWorkflowStatus()
            ]);
        };

        const selectTournament = async (tournamentId) => {
            try {
                const res = await fetch(`/api/tournaments/${tournamentId}`);
                selectedTournamentData.value = await res.json();
                tournamentModalStage.value = 'PLAYOFF';
                tournamentModalView.value = 'bracket';
                finishForm.value = {
                    winner_id: selectedTournamentData.value.winner_id || '',
                    runner_up_id: selectedTournamentData.value.runner_up_id || '',
                    third_place_id: selectedTournamentData.value.third_place_id || '',
                    fourth_place_id: selectedTournamentData.value.fourth_place_id || ''
                };
            } catch (e) {
                console.error("Error fetching tournament details:", e);
            }
        };

        const getAvailableTeamsForTournament = (tourney) => {
            if (!tourney) return teams.value;
            if (tourney.region_id && tourney.region_id !== 'GLOBAL') {
                return teams.value.filter(t => t.region_id === tourney.region_id);
            }
            return teams.value;
        };

        const submitFinishTournament = async () => {
            if (!selectedTournamentData.value) return;
            try {
                const res = await fetch(`/api/tournaments/${selectedTournamentData.value.id}/finish`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(finishForm.value)
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "Gagal menyimpan hasil turnamen");
                alert(data.message);
                await refreshAll();
                await selectTournament(selectedTournamentData.value.id);
            } catch (e) {
                alert("Error: " + e.message);
            }
        };

        const openEditMatchModal = (m) => {
            editingMatch.value = m;
            matchEditForm.value = {
                score1: m.score1 !== null ? m.score1 : 0,
                score2: m.score2 !== null ? m.score2 : 0,
                winner_id: m.winner_id || '',
                status: m.status || 'COMPLETED'
            };
        };

        const onScoreInputAutoWinner = () => {
            if (!editingMatch.value) return;
            const s1 = parseInt(matchEditForm.value.score1);
            const s2 = parseInt(matchEditForm.value.score2);
            if (!isNaN(s1) && !isNaN(s2)) {
                if (s1 > s2) matchEditForm.value.winner_id = editingMatch.value.team1_id;
                else if (s2 > s1) matchEditForm.value.winner_id = editingMatch.value.team2_id;
                else matchEditForm.value.winner_id = '';
            }
        };

        const saveMatchScore = async () => {
            if (!editingMatch.value) return;
            try {
                const res = await fetch(`/api/matches/${editingMatch.value.id}/update`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(matchEditForm.value)
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "Gagal memperbarui skor pertandingan");
                editingMatch.value = null;
                if (selectedTournamentData.value) {
                    await selectTournament(selectedTournamentData.value.id);
                }
            } catch (e) {
                alert("Error: " + e.message);
            }
        };

        const openTeamTrophyCabinet = async (team) => {
            try {
                const res = await fetch(`/api/trophies/history?team_id=${team.id}`);
                const trophies = await res.json();
                selectedTeamForCabinet.value = {
                    ...team,
                    trophies_detail: trophies.map(t => ({
                        image: t.trophy_image,
                        title: t.trophy_title,
                        season: t.season,
                        placement: t.placement,
                        points: t.points,
                        tournament_name: t.tournament_name
                    }))
                };
            } catch (e) {
                console.error("Error fetching team trophies:", e);
            }
        };

        // Workflow Action Handlers
        const createMslTournament = async () => {
            try {
                const res = await fetch(`/api/season/${workflowData.value.season}/create-msl`, { method: 'POST' });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "Gagal membuat MSL");
                alert(data.message);
                await refreshAll();
            } catch (e) {
                alert("Error: " + e.message);
            }
        };

        const createMTournament = async () => {
            try {
                const res = await fetch(`/api/season/${workflowData.value.season}/create-m-championship`, { method: 'POST' });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "Gagal membuat M-Championship");
                alert(data.message);
                await refreshAll();
            } catch (e) {
                alert("Error: " + e.message);
            }
        };

        const startNewSeason = async () => {
            if (!confirm(`Apakah Anda yakin ingin memulai Season ${workflowData.value.season + 1}? Seluruh turnamen MPL untuk season baru akan otomatis dibuat.`)) return;
            try {
                const res = await fetch('/api/season/start-new', { method: 'POST' });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "Gagal memulai season baru");
                alert(data.message);
                selectedSeasonWorkflow.value = workflowData.value.season + 1;
                await refreshAll();
            } catch (e) {
                alert("Error: " + e.message);
            }
        };

        // Simulator actions
        const simulateSeaS4 = async () => {
            try {
                const res = await fetch('/api/simulate/sea-s4?winner_id=YG&runner_up_id=CFU&third_place_id=PRX&fourth_place_id=VPE', {
                    method: 'POST'
                });
                const data = await res.json();
                alert(data.message);
                await refreshAll();
            } catch (e) {
                alert("Error simulating SEA S4: " + e);
            }
        };

        const resetSeaS4 = async () => {
            try {
                const res = await fetch('/api/reset-sea-s4', { method: 'POST' });
                const data = await res.json();
                alert(data.message);
                await refreshAll();
            } catch (e) {
                alert("Error resetting SEA S4: " + e);
            }
        };

        const saveSettings = async () => {
            try {
                const res = await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settingsForm.value)
                });
                const data = await res.json();
                openSettingsModal.value = false;
                await refreshAll();
                alert(data.message);
            } catch (e) {
                alert("Error saving settings: " + e);
            }
        };

        // Computed properties
        const filteredTeams = computed(() => {
            if (!selectedRegionFilter.value) return teams.value;
            return teams.value.filter(t => t.region_id === selectedRegionFilter.value);
        });

        const filteredTournaments = computed(() => {
            if (tournamentTypeFilter.value === 'ALL') return tournaments.value;
            return tournaments.value.filter(t => t.type === tournamentTypeFilter.value);
        });

        const filteredTrophiesHistory = computed(() => {
            if (!selectedTrophySeasonFilter.value) return trophiesHistory.value;
            return trophiesHistory.value.filter(th => th.season === parseInt(selectedTrophySeasonFilter.value));
        });

        const confirmedM4Count = computed(() => {
            if (!roadData.value.m_championship?.slots) return 0;
            return roadData.value.m_championship.slots.filter(s => s.status === 'CONFIRMED').length;
        });

        const confirmedMslCount = computed(() => {
            if (!roadData.value.msl_championship?.slots) return 0;
            return roadData.value.msl_championship.slots.filter(s => s.status === 'CONFIRMED').length;
        });

        // Bracket & Swiss Stage Computed Properties
        const tournamentPlayoffMatches = computed(() => {
            if (!selectedTournamentData.value?.matches) return [];
            return selectedTournamentData.value.matches.filter(m => m.stage === 'PLAYOFF' || !m.stage);
        });

        const tournamentSwissMatches = computed(() => {
            if (!selectedTournamentData.value?.matches) return [];
            return selectedTournamentData.value.matches.filter(m => m.stage === 'SWISS');
        });

        const hasSwissStage = computed(() => {
            return tournamentSwissMatches.value.length > 0;
        });

        const currentStageMatches = computed(() => {
            if (tournamentModalStage.value === 'SWISS') {
                return tournamentSwissMatches.value;
            }
            return [...tournamentPlayoffMatches.value, ...playoffQualifierMatches.value];
        });

        const playoffUpperRounds = computed(() => {
            const isMpl = selectedTournamentData.value?.type === 'MPL';
            const matches = tournamentPlayoffMatches.value.filter(m => m.bracket_type === 'UPPER');
            const r1 = matches.filter(m => ['Match 1', 'Match 2', 'Match 3', 'Match 4'].includes(m.round_name));
            const r2 = matches.filter(m => ['Match 5', 'Match 6'].includes(m.round_name));
            const r3 = matches.filter(m => ['Upper Final', 'Up Final', 'Final Upper'].includes(m.round_name));
            
            const rounds = [];
            if (r1.length) rounds.push({ name: isMpl ? 'Upper Semifinals' : 'Upper Quarterfinals', matches: r1 });
            if (r2.length) rounds.push({ name: 'Upper Semifinals', matches: r2 });
            if (r3.length) rounds.push({ name: isMpl ? 'Final Upper' : 'Upper Final', matches: r3 });
            return rounds;
        });

        const playoffLowerRounds = computed(() => {
            const isMpl = selectedTournamentData.value?.type === 'MPL';
            const matches = tournamentPlayoffMatches.value.filter(m => m.bracket_type === 'LOWER');
            const r1 = matches.filter(m => ['Match 7', 'Match 8'].includes(m.round_name));
            const r2 = matches.filter(m => ['Match 9', 'Match 10'].includes(m.round_name));
            const r3 = matches.filter(m => ['Lower Semifinal', 'Low SF', 'Match 4'].includes(m.round_name));
            const r4 = matches.filter(m => ['Lower Final', 'Low Final', 'Final Lower'].includes(m.round_name));
            
            const rounds = [];
            if (r1.length) rounds.push({ name: 'Lower Round 1', matches: r1 });
            if (r2.length) rounds.push({ name: 'Lower Quarterfinals', matches: r2 });
            if (r3.length) rounds.push({ name: isMpl ? 'Lower Semifinal' : 'Lower Semifinals', matches: r3 });
            if (r4.length) rounds.push({ name: isMpl ? 'Final Lower' : 'Lower Final', matches: r4 });
            return rounds;
        });

        const playoffQualifierMatches = computed(() => {
            if (!selectedTournamentData.value?.matches) return [];
            return selectedTournamentData.value.matches.filter(m => m.bracket_type === 'QUALIFIER');
        });

        const playoffGrandFinal = computed(() => {
            return tournamentPlayoffMatches.value.find(m => m.bracket_type === 'FINAL' || m.round_name === 'Grand Final') || null;
        });

        const swissRounds = computed(() => {
            const matches = tournamentSwissMatches.value;
            if (!matches.length) return [];
            
            return [
                {
                    roundTitle: 'Ronde 1',
                    poolName: 'Pool 0-0 (16 Tim)',
                    badge: '8 Match BO1',
                    badgeClass: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
                    matches: matches.filter(m => m.round_name === 'Round 1')
                },
                {
                    roundTitle: 'Ronde 2',
                    poolName: 'Pool 1-0 & Pool 0-1',
                    badge: '8 Match BO1',
                    badgeClass: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
                    matches: matches.filter(m => m.round_name.includes('Round 2'))
                },
                {
                    roundTitle: 'Ronde 3',
                    poolName: 'Pool 2-0, 1-1, 0-2',
                    badge: '8 Match (BO3 & BO1)',
                    badgeClass: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
                    matches: matches.filter(m => m.round_name.includes('Round 3'))
                },
                {
                    roundTitle: 'Ronde 4',
                    poolName: 'Pool 2-1 & Pool 1-2',
                    badge: '6 Match BO3',
                    badgeClass: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
                    matches: matches.filter(m => m.round_name.includes('Round 4'))
                },
                {
                    roundTitle: 'Ronde 5 (Decider)',
                    poolName: 'Pool 2-2',
                    badge: '3 Match BO3 Decider',
                    badgeClass: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
                    matches: matches.filter(m => m.round_name.includes('Round 5'))
                }
            ];
        });

        const swissQualifiedTeams = computed(() => {
            const matches = tournamentSwissMatches.value;
            if (!matches.length) return [];
            const qWinners = [];
            const r3High = matches.filter(m => m.bracket_type.includes('2-0'));
            const r4High = matches.filter(m => m.bracket_type.includes('2-1'));
            const r5 = matches.filter(m => m.bracket_type.includes('2-2'));
            
            [...r3High, ...r4High, ...r5].forEach(m => {
                if (m.winner_id) {
                    const tName = m.winner_id === m.team1_id ? m.team1_name : m.team2_name;
                    const tLogo = m.winner_id === m.team1_id ? m.team1_logo : m.team2_logo;
                    qWinners.push({ id: m.winner_id, name: tName || m.winner_id, logo: tLogo });
                }
            });
            return qWinners;
        });

        const swissEliminatedTeams = computed(() => {
            const matches = tournamentSwissMatches.value;
            if (!matches.length) return [];
            const elim = [];
            const r3Low = matches.filter(m => m.bracket_type.includes('0-2'));
            const r4Low = matches.filter(m => m.bracket_type.includes('1-2'));
            const r5 = matches.filter(m => m.bracket_type.includes('2-2'));
            
            [...r3Low, ...r4Low, ...r5].forEach(m => {
                if (m.loser_id) {
                    const tName = m.loser_id === m.team1_id ? m.team1_name : m.team2_name;
                    const tLogo = m.loser_id === m.team1_id ? m.team1_logo : m.team2_logo;
                    elim.push({ id: m.loser_id, name: tName || m.loser_id, logo: tLogo });
                }
            });
            return elim;
        });

        onMounted(() => {
            refreshAll();
        });

        return {
            currentTab,
            tabs,
            mobileMenuOpen,
            openSettingsModal,
            stats,
            teams,
            regions,
            tournaments,
            roadData,
            selectedTournamentData,
            selectedRegionFilter,
            tournamentTypeFilter,
            settingsForm,
            availableSeasons,
            filteredTeams,
            filteredTournaments,
            confirmedM4Count,
            confirmedMslCount,
            trophiesHistory,
            selectedTrophySeasonFilter,
            filteredTrophiesHistory,
            selectedSeasonWorkflow,
            workflowData,
            selectedTeamForCabinet,
            tournamentModalView,
            tournamentModalStage,
            tournamentPlayoffMatches,
            tournamentSwissMatches,
            hasSwissStage,
            currentStageMatches,
            playoffUpperRounds,
            playoffLowerRounds,
            playoffQualifierMatches,
            playoffGrandFinal,
            swissRounds,
            swissQualifiedTeams,
            swissEliminatedTeams,
            editingMatch,
            matchEditForm,
            openEditMatchModal,
            onScoreInputAutoWinner,
            saveMatchScore,
            finishForm,
            getAvailableTeamsForTournament,
            submitFinishTournament,
            selectTournament,
            openTeamTrophyCabinet,
            createMslTournament,
            createMTournament,
            startNewSeason,
            fetchWorkflowStatus,
            simulateSeaS4,
            resetSeaS4,
            saveSettings,
            refreshAll
        };
    }
}).mount('#app');
