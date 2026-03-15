import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';

import ErrorBoundary from '../ErrorBoundary';
import { SkeletonChart } from '../components/Dashboard/SkeletonLoaders';
import { getDrugAEGraph } from '../services/api';

const GRAPH_HEIGHT = 800;
const EDGE_DEFAULT = '#1a4a35';
const EDGE_HIGHLIGHT = '#00C896';
const NODE_COLORS = {
    drug: '#1D9E75',
    ae: '#EF9F27',
    outcome: '#8B5CF6',
};
const DISPLAY_NAMES = {
    semaglutide: 'Ozempic/Wegovy',
    metformin: 'Metformin',
    liraglutide: 'Victoza',
    dulaglutide: 'Trulicity',
    empagliflozin: 'Jardiance',
    glipizide: 'Glipizide',
    dapagliflozin: 'Farxiga',
    sitagliptin: 'Januvia',
};

const cleanLabel = (raw = '') =>
    raw
        .replace(/_/g, ' ')
        .split(' ')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ')
        .replace(/'\w/g, (match) => match.toLowerCase());

const getDisplayName = (id = '') => DISPLAY_NAMES[id] || id.charAt(0).toUpperCase() + id.slice(1);

const getNodeDisplayName = (node) => {
    if (!node) return '';
    return node.type === 'drug' ? getDisplayName(node.id) : cleanLabel(node.label || node.id);
};

const getDrugCircleLabel = (node) => {
    const label = getDisplayName(node.id).split('/')[0];
    return label.split(' ')[0];
};

const getNodeRadius = (node) => {
    if (node.type === 'drug') return 20;
    if (node.type === 'outcome') return 12;
    return 9;
};

const getCollisionRadius = (node) => {
    if (node.type === 'drug') return 55;
    if (node.type === 'ae') return 28;
    return 34;
};

const getTypeMeta = (type) => {
    if (type === 'drug') {
        return {
            badge: 'Medication',
            color: '#00C896',
            background: 'rgba(0,200,150,0.14)',
        };
    }

    if (type === 'outcome') {
        return {
            badge: 'Outcome',
            color: '#8B5CF6',
            background: 'rgba(139,92,246,0.16)',
        };
    }

    return {
        badge: 'Side Effect',
        color: '#EF9F27',
        background: 'rgba(239,159,39,0.16)',
    };
};

const getHighlightedFromPills = (selectedDrugs, nodes, neighborMap) => {
    const ids = new Set();

    selectedDrugs.forEach((drugId) => {
        ids.add(drugId);
        (neighborMap.get(drugId) || new Set()).forEach((neighborId) => {
            const neighbor = nodes.find((node) => node.id === neighborId);
            if (neighbor && neighbor.type !== 'drug') ids.add(neighborId);
        });
    });

    return ids;
};

const getHighlightedFromClick = (clickedNodeId, neighborMap) => {
    const ids = new Set();
    if (!clickedNodeId) return ids;

    ids.add(clickedNodeId);
    (neighborMap.get(clickedNodeId) || new Set()).forEach((neighborId) => ids.add(neighborId));
    return ids;
};

function ErrorCard({ error, onRetry }) {
    return (
        <div className="di-card">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <h2 className="text-lg font-semibold text-di-text">Medication Side Effect Network</h2>
                    <p className="mt-1 text-sm text-di-text-secondary">{error || 'Failed to load graph data.'}</p>
                </div>
                <button type="button" className="di-btn-secondary" onClick={onRetry}>
                    Retry
                </button>
            </div>
        </div>
    );
}

function DrugPill({ drugId, isSelected, onToggle }) {
    return (
        <button
            type="button"
            onClick={() => onToggle(drugId)}
            style={{
                background: isSelected ? 'rgba(0,200,150,0.15)' : 'transparent',
                border: isSelected ? '2px solid #00C896' : '1px solid rgba(255,255,255,0.15)',
                borderRadius: '999px',
                color: isSelected ? '#00C896' : 'rgba(255,255,255,0.5)',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: isSelected ? 700 : 500,
                padding: '8px 14px',
                transition: 'all 180ms ease',
                whiteSpace: 'nowrap',
            }}
        >
            {getDisplayName(drugId)}
        </button>
    );
}

function NodeInfoPanel({ node, neighborCount, onClose }) {
    if (!node) return null;

    const typeMeta = getTypeMeta(node.type);

    return (
        <div
            style={{
                position: 'absolute',
                top: '12px',
                right: '12px',
                background: 'rgba(7,20,14,0.95)',
                border: '1px solid rgba(0,200,150,0.25)',
                borderRadius: '10px',
                padding: '14px 18px',
                minWidth: '200px',
                zIndex: 10,
                backdropFilter: 'blur(10px)',
            }}
        >
            <button
                type="button"
                onClick={onClose}
                style={{
                    position: 'absolute',
                    top: '10px',
                    right: '12px',
                    background: 'transparent',
                    border: 'none',
                    color: '#00C896',
                    cursor: 'pointer',
                    fontSize: '13px',
                    fontWeight: 600,
                    padding: 0,
                }}
            >
                {'\u2715 Close'}
            </button>
            <div
                style={{
                    color: '#FFFFFF',
                    fontSize: '15px',
                    fontWeight: 700,
                    marginBottom: '10px',
                    paddingRight: '70px',
                }}
            >
                {getNodeDisplayName(node)}
            </div>
            <span
                style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    background: typeMeta.background,
                    borderRadius: '999px',
                    color: typeMeta.color,
                    fontSize: '11px',
                    fontWeight: 700,
                    marginBottom: '10px',
                    padding: '4px 10px',
                }}
            >
                {typeMeta.badge}
            </span>
            <div style={{ color: 'rgba(255,255,255,0.58)', fontSize: '12px' }}>
                {neighborCount} direct connection{neighborCount === 1 ? '' : 's'}
            </div>
        </div>
    );
}

function KnowledgeGraphPage() {
    const [graphData, setGraphData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedDrugs, setSelectedDrugs] = useState(new Set());
    const [clickedNodeId, setClickedNodeId] = useState(null);
    const [graphWidth, setGraphWidth] = useState(0);

    const containerRef = useRef(null);
    const svgRef = useRef(null);
    const nodeSelectionRef = useRef(null);
    const linkSelectionRef = useRef(null);
    const clickedNodeIdRef = useRef(null);
    const selectedDrugsRef = useRef(new Set());
    const resetViewRef = useRef(() => {});

    const loadGraph = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await getDrugAEGraph();
            setGraphData(response.data);
        } catch (requestError) {
            setError(requestError.response?.data?.detail || requestError.message || 'Unable to load graph.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadGraph();
    }, [loadGraph]);

    useEffect(() => {
        clickedNodeIdRef.current = clickedNodeId;
    }, [clickedNodeId]);

    useEffect(() => {
        selectedDrugsRef.current = selectedDrugs;
    }, [selectedDrugs]);

    useEffect(() => {
        if (!graphData || !containerRef.current) return undefined;

        const updateWidth = () => {
            setGraphWidth(containerRef.current?.clientWidth || 0);
        };

        updateWidth();

        const observer = new ResizeObserver(updateWidth);
        observer.observe(containerRef.current);

        return () => observer.disconnect();
    }, [graphData]);

    const normalizedGraph = useMemo(() => {
        if (!graphData) {
            return {
                nodes: [],
                edges: [],
                neighborMap: new Map(),
                nodeMap: new Map(),
                stats: { ae_nodes: 0, drug_nodes: 0, total_edges: 0 },
            };
        }

        const nodes = graphData.nodes.map((node) => ({
            ...node,
            cleanLabel: cleanLabel(node.label || node.id),
            displayName: getNodeDisplayName(node),
        }));
        const nodeMap = new Map(nodes.map((node) => [node.id, node]));
        const edges = graphData.edges.map((edge, index) => ({
            ...edge,
            id: `${typeof edge.source === 'object' ? edge.source.id : edge.source}-${typeof edge.target === 'object' ? edge.target.id : edge.target}-${edge.type || 'edge'}-${index}`,
        }));
        const neighborMap = new Map();

        edges.forEach((edge) => {
            const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
            const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;

            if (!neighborMap.has(sourceId)) neighborMap.set(sourceId, new Set());
            if (!neighborMap.has(targetId)) neighborMap.set(targetId, new Set());

            neighborMap.get(sourceId).add(targetId);
            neighborMap.get(targetId).add(sourceId);
        });

        return {
            nodes,
            edges,
            neighborMap,
            nodeMap,
            stats: graphData.stats || {
                ae_nodes: nodes.filter((node) => node.type === 'ae').length,
                drug_nodes: nodes.filter((node) => node.type === 'drug').length,
                total_edges: edges.length,
            },
        };
    }, [graphData]);

    const drugNodes = useMemo(() => {
        const seen = new Map();

        normalizedGraph.nodes
            .filter((node) => node.type === 'drug')
            .forEach((node) => {
                const displayName = getDisplayName(node.id);
                if (!seen.has(displayName) || (node.size || 0) > (seen.get(displayName).size || 0)) {
                    seen.set(displayName, node);
                }
            });

        return Array.from(seen.values()).sort((left, right) => getDisplayName(left.id).localeCompare(getDisplayName(right.id)));
    }, [normalizedGraph.nodes]);

    const clickedNode = useMemo(
        () => normalizedGraph.nodeMap.get(clickedNodeId) || null,
        [clickedNodeId, normalizedGraph.nodeMap]
    );

    const clickedNodeNeighborCount = useMemo(
        () => (clickedNodeId ? normalizedGraph.neighborMap.get(clickedNodeId)?.size || 0 : 0),
        [clickedNodeId, normalizedGraph.neighborMap]
    );

    const handleDrugToggle = useCallback((drugId) => {
        setSelectedDrugs((current) => {
            const next = new Set(current);
            if (next.has(drugId)) {
                next.delete(drugId);
            } else {
                next.add(drugId);
            }
            return next;
        });
    }, []);

    const clearAllSelections = useCallback(() => {
        setClickedNodeId(null);
        setSelectedDrugs(new Set());
    }, []);

    const handleSoftReset = useCallback(() => {
        if (clickedNodeIdRef.current) {
            setClickedNodeId(null);
            return;
        }

        if (selectedDrugsRef.current.size > 0) {
            setSelectedDrugs(new Set());
        }
    }, []);

    useEffect(() => {
        const onKeyDown = (event) => {
            if (event.key === 'Escape') {
                handleSoftReset();
            }
        };

        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    }, [handleSoftReset]);

    useEffect(() => {
        if (!svgRef.current || normalizedGraph.nodes.length === 0) return undefined;

        const width = graphWidth || containerRef.current?.clientWidth || 960;
        const height = GRAPH_HEIGHT;
        const svg = d3.select(svgRef.current);
        const nodes = normalizedGraph.nodes.map((node) => ({ ...node }));
        const edges = normalizedGraph.edges.map((edge) => ({ ...edge }));
        const nodeCount = nodes.length;
        const edgeCount = edges.length;
        const linkDistance = edgeCount > 0 ? Math.min(200, width / Math.sqrt(edgeCount)) : 200;
        const prerunTicks = Math.max(1, Math.ceil(300 / Math.log(nodeCount + 1)));

        svg.selectAll('*').remove();
        svg
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('viewBox', `0 0 ${width} ${height}`)
            .attr('preserveAspectRatio', 'xMidYMid meet');

        const defs = svg.append('defs');
        const glow = defs
            .append('filter')
            .attr('id', 'knowledge-graph-glow')
            .attr('x', '-50%')
            .attr('y', '-50%')
            .attr('width', '200%')
            .attr('height', '200%');
        glow.append('feGaussianBlur').attr('stdDeviation', 5).attr('result', 'blur');
        const merge = glow.append('feMerge');
        merge.append('feMergeNode').attr('in', 'blur');
        merge.append('feMergeNode').attr('in', 'SourceGraphic');

        const background = svg
            .append('rect')
            .attr('width', width)
            .attr('height', height)
            .attr('fill', 'transparent')
            .style('cursor', 'grab')
            .on('click', (event) => {
                event.stopPropagation();
                handleSoftReset();
            })
            .on('dblclick', (event) => {
                event.stopPropagation();
                clearAllSelections();
                resetViewRef.current();
            });

        const zoomLayer = svg.append('g');
        const linkLayer = zoomLayer.append('g');
        const nodeLayer = zoomLayer.append('g');

        const zoomBehavior = d3
            .zoom()
            .scaleExtent([0.25, 4])
            .on('zoom', (event) => {
                zoomLayer.attr('transform', event.transform);
            });

        svg.call(zoomBehavior).on('dblclick.zoom', null);
        resetViewRef.current = () => {
            svg.transition().duration(250).call(zoomBehavior.transform, d3.zoomIdentity);
        };

        const simulation = d3
            .forceSimulation(nodes)
            .force(
                'link',
                d3
                    .forceLink(edges)
                    .id((node) => node.id)
                    .distance(linkDistance)
                    .strength((edge) => (edge.type === 'drug_combination' ? 0.3 : 0.62))
            )
            .force(
                'charge',
                d3.forceManyBody().strength((node) => {
                    if (node.type === 'drug') return -820;
                    if (node.type === 'outcome') return -360;
                    return -230;
                })
            )
            .force('x', d3.forceX(width / 2).strength(0.15))
            .force('y', d3.forceY(height / 2).strength(0.15))
            .force('collision', d3.forceCollide().radius((node) => getCollisionRadius(node)).strength(1))
            .stop();

        for (let tick = 0; tick < prerunTicks; tick += 1) {
            simulation.tick();
        }

        nodes.forEach((node) => {
            node.x = Math.max(50, Math.min(width - 50, node.x || width / 2));
            node.y = Math.max(50, Math.min(height - 50, node.y || height / 2));
        });

        const link = linkLayer
            .selectAll('line')
            .data(edges, (edge) => edge.id)
            .join('line')
            .attr('stroke', EDGE_DEFAULT)
            .attr('stroke-linecap', 'round')
            .attr('stroke-opacity', 0.55)
            .attr('stroke-width', (edge) => Math.max(0.3, Math.sqrt(edge.weight || 1) * 0.25));

        const node = nodeLayer
            .selectAll('g')
            .data(nodes, (graphNode) => graphNode.id)
            .join('g')
            .style('cursor', 'pointer')
            .call(
                d3
                    .drag()
                    .on('start', (event, graphNode) => {
                        background.style('cursor', 'grabbing');
                        if (!event.active) simulation.alphaTarget(0.22).restart();
                        graphNode.fx = graphNode.x;
                        graphNode.fy = graphNode.y;
                    })
                    .on('drag', (event, graphNode) => {
                        graphNode.fx = event.x;
                        graphNode.fy = event.y;
                    })
                    .on('end', (event, graphNode) => {
                        background.style('cursor', 'grab');
                        if (!event.active) simulation.alphaTarget(0);
                        graphNode.fx = null;
                        graphNode.fy = null;
                    })
            )
            .on('click', (event, graphNode) => {
                event.stopPropagation();
                setClickedNodeId((current) => (current === graphNode.id ? null : graphNode.id));
            });

        node
            .append('circle')
            .attr('r', (graphNode) => getNodeRadius(graphNode))
            .attr('fill', (graphNode) => NODE_COLORS[graphNode.type] || NODE_COLORS.ae)
            .attr('stroke', '#FFFFFF')
            .attr('stroke-width', (graphNode) => {
                if (graphNode.type === 'drug') return 2;
                if (graphNode.type === 'outcome') return 1;
                return 0.8;
            });

        node
            .filter((graphNode) => graphNode.type === 'drug')
            .append('text')
            .text((graphNode) => getDrugCircleLabel(graphNode))
            .attr('fill', '#FFFFFF')
            .attr('font-size', 13)
            .attr('font-weight', 700)
            .attr('lengthAdjust', 'spacingAndGlyphs')
            .attr('pointer-events', 'none')
            .attr('text-anchor', 'middle')
            .attr('textLength', 32)
            .attr('dominant-baseline', 'central');

        const nonDrugNodes = node.filter((graphNode) => graphNode.type !== 'drug');

        nonDrugNodes
            .append('rect')
            .attr('width', (graphNode) => graphNode.cleanLabel.length * 6.5 + 8)
            .attr('height', 16)
            .attr('fill', 'rgba(7,15,12,0.9)')
            .attr('rx', 3)
            .attr('x', 12)
            .attr('y', -8)
            .attr('pointer-events', 'none');

        nonDrugNodes
            .append('text')
            .text((graphNode) => graphNode.cleanLabel)
            .attr('fill', '#F4F7F5')
            .attr('font-size', 11)
            .attr('pointer-events', 'none')
            .attr('text-anchor', 'start')
            .attr('dominant-baseline', 'central')
            .attr('dx', 14);

        const positionGraph = () => {
            link
                .attr('x1', (edge) => edge.source.x)
                .attr('y1', (edge) => edge.source.y)
                .attr('x2', (edge) => edge.target.x)
                .attr('y2', (edge) => edge.target.y);

            node.attr('transform', (graphNode) => `translate(${graphNode.x},${graphNode.y})`);
        };

        positionGraph();

        simulation.on('tick', positionGraph);
        simulation.alpha(0.12).restart();

        nodeSelectionRef.current = node;
        linkSelectionRef.current = link;

        return () => {
            simulation.stop();
            nodeSelectionRef.current = null;
            linkSelectionRef.current = null;
            svg.on('.zoom', null);
        };
    }, [clearAllSelections, graphWidth, handleSoftReset, normalizedGraph.edges, normalizedGraph.nodes]);

    useEffect(() => {
        const nodeSelection = nodeSelectionRef.current;
        const linkSelection = linkSelectionRef.current;
        if (!nodeSelection || !linkSelection) return;

        const highlighted = clickedNodeId
            ? getHighlightedFromClick(clickedNodeId, normalizedGraph.neighborMap)
            : getHighlightedFromPills(selectedDrugs, normalizedGraph.nodes, normalizedGraph.neighborMap);
        const hasSelection = Boolean(clickedNodeId) || selectedDrugs.size > 0;

        nodeSelection.style('opacity', (graphNode) => (hasSelection ? (highlighted.has(graphNode.id) ? 1 : 0.06) : 1));

        nodeSelection
            .select('circle')
            .attr('filter', (graphNode) => {
                if (!hasSelection) return null;
                return highlighted.has(graphNode.id) ? 'url(#knowledge-graph-glow)' : null;
            });

        linkSelection
            .attr('stroke', (edge) => {
                const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                return hasSelection && highlighted.has(sourceId) && highlighted.has(targetId) ? EDGE_HIGHLIGHT : EDGE_DEFAULT;
            })
            .attr('stroke-opacity', (edge) => {
                if (!hasSelection) return 0.55;
                const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                return highlighted.has(sourceId) && highlighted.has(targetId) ? 1 : 0.03;
            })
            .attr('stroke-width', (edge) => {
                if (!hasSelection) return Math.max(0.3, Math.sqrt(edge.weight || 1) * 0.25);
                const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                return highlighted.has(sourceId) && highlighted.has(targetId)
                    ? 2
                    : Math.max(0.3, Math.sqrt(edge.weight || 1) * 0.25);
            });
    }, [clickedNodeId, normalizedGraph.neighborMap, normalizedGraph.nodes, selectedDrugs]);

    const stats = normalizedGraph.stats;

    return (
        <ErrorBoundary>
            <div className="space-y-6 animate-fade-in">
                <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-di-text">Medication Side Effect Network</h1>
                        <p className="mt-2 max-w-3xl text-sm text-di-text-secondary">
                            Connections between medications and patient-reported side effects. Node size reflects report frequency.
                        </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-4 text-sm text-di-text-secondary">
                        <div className="flex items-center gap-2">
                            <span className="h-3 w-3 rounded-full" style={{ backgroundColor: NODE_COLORS.drug }} />
                            <span>Medication</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="h-3 w-3 rounded-full" style={{ backgroundColor: NODE_COLORS.ae }} />
                            <span>Side Effect</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="h-3 w-3 rounded-full" style={{ backgroundColor: NODE_COLORS.outcome }} />
                            <span>Outcome</span>
                        </div>
                    </div>
                </div>

                {error ? (
                    <ErrorCard error={error} onRetry={loadGraph} />
                ) : loading && !graphData ? (
                    <SkeletonChart height="h-[800px]" />
                ) : (
                    <>
                        <div className="di-card" style={{ padding: '18px 20px' }}>
                            <div className="flex flex-wrap items-center gap-3">
                                {drugNodes.map((node) => (
                                    <DrugPill
                                        key={node.id}
                                        drugId={node.id}
                                        isSelected={selectedDrugs.has(node.id)}
                                        onToggle={handleDrugToggle}
                                    />
                                ))}
                                {selectedDrugs.size > 0 && (
                                    <button
                                        type="button"
                                        className="di-btn-secondary"
                                        onClick={() => setSelectedDrugs(new Set())}
                                        style={{ padding: '8px 12px' }}
                                    >
                                        Clear
                                    </button>
                                )}
                            </div>
                            <p className="mt-4 text-sm text-di-text-secondary">
                                Click a medication pill to highlight its side effects. Click any node for details. Drag to reposition.
                                Scroll to zoom.
                            </p>
                        </div>

                        <div className="di-card" style={{ padding: 0, overflow: 'hidden' }}>
                            <div
                                ref={containerRef}
                                style={{
                                    height: `${GRAPH_HEIGHT}px`,
                                    background: 'radial-gradient(ellipse at center, #0a1f14 0%, #050e09 100%)',
                                    border: '1px solid rgba(0,200,150,0.1)',
                                    borderRadius: '12px',
                                    overflow: 'hidden',
                                    position: 'relative',
                                }}
                            >
                                <button
                                    type="button"
                                    className="di-btn-secondary"
                                    onClick={() => resetViewRef.current()}
                                    style={{
                                        position: 'absolute',
                                        top: '12px',
                                        left: '12px',
                                        padding: '7px 12px',
                                        zIndex: 10,
                                    }}
                                >
                                    Reset view
                                </button>
                                <svg ref={svgRef} className="h-full w-full" width="100%" height="100%" />
                                <NodeInfoPanel node={clickedNode} neighborCount={clickedNodeNeighborCount} onClose={() => setClickedNodeId(null)} />
                            </div>
                        </div>

                        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                            <div className="di-card">
                                <div className="text-3xl font-bold" style={{ color: '#00C896' }}>
                                    {stats.drug_nodes || 0}
                                </div>
                                <div className="mt-2 text-sm text-di-text-secondary">Medications</div>
                            </div>
                            <div className="di-card">
                                <div className="text-3xl font-bold" style={{ color: NODE_COLORS.ae }}>
                                    {stats.ae_nodes || 0}
                                </div>
                                <div className="mt-2 text-sm text-di-text-secondary">Side Effects</div>
                            </div>
                            <div className="di-card">
                                <div className="text-3xl font-bold text-di-text">{stats.total_edges || normalizedGraph.edges.length}</div>
                                <div className="mt-2 text-sm text-di-text-secondary">Reported Connections</div>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </ErrorBoundary>
    );
}

export default KnowledgeGraphPage;
