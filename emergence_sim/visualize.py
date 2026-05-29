"""Pygame primary visualizer with matplotlib fallback."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from emergence_sim.agents import AGENT_PROFILES, get_trust
from emergence_sim.config import GRID_SIZE, LANDMARK_LABELS, LANDMARKS
from emergence_sim.engine import EmergenceSimulation
from emergence_sim.metrics import build_relationship_graph

try:
    import pygame

    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False


def _circle_layout(names: list[str], cx: float, cy: float, radius: float) -> dict[str, tuple[float, float]]:
    pos = {}
    n = len(names)
    for i, name in enumerate(sorted(names)):
        angle = 2 * math.pi * i / max(1, n)
        pos[name] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
    return pos


class BaseVisualizer(ABC):
    @abstractmethod
    def run(self, sim: EmergenceSimulation, *, steps_per_frame: int = 2, fps: int = 8) -> None:
        ...


if HAS_PYGAME:

    class PygameVisualizer(BaseVisualizer):
        CELL = 18
        GRID_PX = GRID_SIZE * 18
        WIDTH = 1280
        HEIGHT = 800
        MARGIN = 12

        def __init__(self) -> None:
            pygame.init()
            pygame.display.set_caption("Emergence World — Educational Simulation")
            self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
            self.clock = pygame.time.Clock()
            self.font = pygame.font.SysFont("dejavusans", 14)
            self.font_sm = pygame.font.SysFont("dejavusans", 12)
            self.font_lg = pygame.font.SysFont("dejavusans", 18, bold=True)

        def _grid_origin(self) -> tuple[int, int]:
            return self.MARGIN, 60

        def draw_grid(self, sim: EmergenceSimulation) -> None:
            ox, oy = self._grid_origin()
            for x in range(GRID_SIZE + 1):
                pygame.draw.line(
                    self.screen,
                    (45, 50, 60),
                    (ox + x * self.CELL, oy),
                    (ox + x * self.CELL, oy + self.GRID_PX),
                    1,
                )
            for y in range(GRID_SIZE + 1):
                pygame.draw.line(
                    self.screen,
                    (45, 50, 60),
                    (ox, oy + y * self.CELL),
                    (ox + self.GRID_PX, oy + y * self.CELL),
                    1,
                )

            for key, (lx, ly) in LANDMARKS.items():
                rx = ox + lx * self.CELL
                ry = oy + ly * self.CELL
                rect = pygame.Rect(rx - 4, ry - 4, 10, 10)
                pygame.draw.rect(self.screen, (90, 90, 110), rect, border_radius=2)
                label = self.font_sm.render(LANDMARK_LABELS.get(key, key)[:10], True, (160, 160, 180))
                self.screen.blit(label, (rx - 20, ry - 18))

            for agent in sim.agents.values():
                if not agent.alive:
                    continue
                profile = AGENT_PROFILES[agent.name]
                ax = ox + agent.x * self.CELL + self.CELL // 2
                ay = oy + agent.y * self.CELL + self.CELL // 2
                pygame.draw.circle(self.screen, profile.color, (ax, ay), 7)
                pygame.draw.circle(self.screen, (255, 255, 255), (ax, ay), 7, 1)
                tag = self.font_sm.render(agent.name[:3], True, (240, 240, 240))
                self.screen.blit(tag, (ax - 10, ay - 22))

        def draw_graph(self, sim: EmergenceSimulation) -> None:
            gx, gy = self.GRID_PX + self.MARGIN * 2, 60
            gw, gh = self.WIDTH - gx - self.MARGIN, 320
            pygame.draw.rect(self.screen, (30, 32, 40), (gx, gy, gw, gh), border_radius=6)
            title = self.font_lg.render("Relationship Graph", True, (220, 220, 230))
            self.screen.blit(title, (gx + 10, gy + 8))

            alive = {a.name for a in sim.alive_agents()}
            if len(alive) < 2:
                return
            g = build_relationship_graph(sim.edges, alive)
            cx, cy = gx + gw // 2, gy + gh // 2 + 10
            pos = _circle_layout(list(alive), cx, cy, min(gw, gh) * 0.32)

            for a, b, data in g.edges(data=True):
                trust = data.get("weight", 0)
                color = (80, 200, 120) if trust > 0.5 else (200, 80, 80) if trust < -0.2 else (120, 120, 140)
                width = max(1, int(abs(trust) * 4))
                p1, p2 = pos[a], pos[b]
                pygame.draw.line(self.screen, color, p1, p2, width)

            for name in alive:
                profile = AGENT_PROFILES[name]
                px, py = pos[name]
                pygame.draw.circle(self.screen, profile.color, (int(px), int(py)), 14)
                pygame.draw.circle(self.screen, (255, 255, 255), (int(px), int(py)), 14, 1)
                lbl = self.font_sm.render(name, True, (230, 230, 240))
                self.screen.blit(lbl, (int(px) - 20, int(py) + 16))

        def draw_metrics(self, sim: EmergenceSimulation) -> None:
            gx = self.GRID_PX + self.MARGIN * 2
            gy = 390
            gw = self.WIDTH - gx - self.MARGIN
            gh = self.HEIGHT - gy - self.MARGIN
            pygame.draw.rect(self.screen, (30, 32, 40), (gx, gy, gw, gh), border_radius=6)
            snap = sim.metrics.latest
            if snap is None:
                return

            title = self.font_lg.render("AWI Dashboard (Educational)", True, (220, 220, 230))
            self.screen.blit(title, (gx + 10, gy + 8))

            bars = [
                ("Population", snap.population_alive / 10.0, (100, 200, 255)),
                ("Crime rate", min(1.0, snap.crime_rate * 20), (255, 100, 100)),
                ("Exploration", snap.exploration_mean / GRID_SIZE, (255, 200, 80)),
                ("Governance", snap.governance_participation, (180, 140, 255)),
                ("Net density", snap.network_density, (80, 220, 160)),
                ("Gini (credits)", snap.gini_credits, (255, 150, 100)),
            ]
            y0 = gy + 40
            for i, (label, val, color) in enumerate(bars):
                y = y0 + i * 28
                pygame.draw.rect(self.screen, (50, 52, 62), (gx + 10, y, gw - 20, 18), border_radius=3)
                w = int((gw - 24) * max(0, min(1, val)))
                pygame.draw.rect(self.screen, color, (gx + 12, y + 2, w, 14), border_radius=3)
                txt = self.font.render(f"{label}: {val:.2f}", True, (200, 200, 210))
                self.screen.blit(txt, (gx + 14, y + 2))

            info_y = y0 + len(bars) * 28 + 10
            lines = [
                f"Day {snap.day}  Tick {snap.tick}  Alliances {snap.alliance_count}  Rivalries {snap.rivalry_count}",
                f"Credits μ={snap.credit_mean:.1f}  Innovations={sim.world.shared_innovations}  Crimes={sim.world.crimes_total}",
            ]
            for j, line in enumerate(lines):
                self.screen.blit(self.font.render(line, True, (170, 175, 190)), (gx + 10, info_y + j * 20))

            log_y = info_y + 50
            self.screen.blit(self.font.render("Recent events:", True, (190, 190, 200)), (gx + 10, log_y))
            for k, ev in enumerate(sim.world.event_log[-5:]):
                ev_s = ev if len(ev) < 70 else ev[:67] + "..."
                self.screen.blit(self.font_sm.render(ev_s, True, (140, 145, 160)), (gx + 10, log_y + 18 + k * 16))

        def draw_header(self, sim: EmergenceSimulation) -> None:
            header = self.font_lg.render(
                "Emergence World — 10 Agent Educational Simulation",
                True,
                (240, 240, 250),
            )
            self.screen.blit(header, (self.MARGIN, 16))
            sub = self.font.render(
                "Inspired by EmergenceAI/Emergence-World (CC BY-NC 4.0) — rule-based emergence demo",
                True,
                (150, 155, 170),
            )
            self.screen.blit(sub, (self.MARGIN, 38))

        def run(self, sim: EmergenceSimulation, *, steps_per_frame: int = 2, fps: int = 8) -> None:
            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key == pygame.K_SPACE:
                            sim.cfg.paused = not sim.cfg.paused

                if not sim.cfg.paused:
                    for _ in range(steps_per_frame):
                        if not sim.step():
                            running = False
                            break

                self.screen.fill((22, 24, 30))
                self.draw_header(sim)
                self.draw_grid(sim)
                self.draw_graph(sim)
                self.draw_metrics(sim)
                pygame.display.flip()
                self.clock.tick(fps)

            pygame.quit()


class MatplotlibVisualizer(BaseVisualizer):
    def run(self, sim: EmergenceSimulation, *, steps_per_frame: int = 2, fps: int = 8) -> None:
        interval = int(1000 / fps)

        fig, axes = plt.subplots(2, 2, figsize=(12, 9))
        fig.suptitle("Emergence World — Educational Simulation", fontsize=14)
        ax_grid, ax_graph, ax_metrics, ax_log = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]

        def update(_frame: int):
            if not sim.cfg.paused:
                for _ in range(steps_per_frame):
                    if not sim.step():
                        plt.close(fig)
                        return []

            ax_grid.clear()
            ax_graph.clear()
            ax_metrics.clear()
            ax_log.clear()

            ax_grid.set_xlim(0, GRID_SIZE)
            ax_grid.set_ylim(0, GRID_SIZE)
            ax_grid.set_aspect("equal")
            ax_grid.set_title("World Grid")
            ax_grid.grid(True, alpha=0.3)
            for key, (lx, ly) in LANDMARKS.items():
                ax_grid.scatter(lx, ly, c="gray", s=40, marker="s")
                ax_grid.annotate(LANDMARK_LABELS.get(key, key)[:8], (lx, ly), fontsize=6, alpha=0.7)

            for agent in sim.agents.values():
                if not agent.alive:
                    continue
                c = np.array(AGENT_PROFILES[agent.name].color) / 255.0
                ax_grid.scatter(agent.x, agent.y, c=[c], s=120, edgecolors="white", linewidths=0.8)
                ax_grid.text(agent.x, agent.y + 0.8, agent.name, ha="center", fontsize=7, color="white")

            alive = {a.name for a in sim.alive_agents()}
            g = build_relationship_graph(sim.edges, alive)
            ax_graph.set_title("Relationships")
            if g.number_of_nodes() > 1:
                pos = nx.spring_layout(g, seed=42, weight="weight")
                colors = []
                for u, v in g.edges():
                    t = get_trust(sim.edges, u, v)
                    colors.append("#50c878" if t > 0.5 else "#e05050" if t < -0.2 else "#888")
                nx.draw_networkx_nodes(
                    g,
                    pos,
                    ax=ax_graph,
                    node_color=[np.array(AGENT_PROFILES[n].color) / 255 for n in g.nodes()],
                    node_size=400,
                )
                nx.draw_networkx_labels(g, pos, ax=ax_graph, font_size=7, font_color="white")
                for (u, v), color in zip(g.edges(), colors):
                    nx.draw_networkx_edges(g, pos, edgelist=[(u, v)], edge_color=color, width=2, ax=ax_graph)

            snap = sim.metrics.latest
            ax_metrics.set_title("AWI Metrics")
            if snap:
                keys = ["Pop", "Crime", "Explore", "Gov", "Density", "Gini"]
                vals = [
                    snap.population_alive / 10,
                    min(1, snap.crime_rate * 20),
                    snap.exploration_mean / GRID_SIZE,
                    snap.governance_participation,
                    snap.network_density,
                    snap.gini_credits,
                ]
                ax_metrics.barh(keys, vals, color=["#64b4ff", "#ff6464", "#ffc850", "#b48cff", "#50dc96", "#ff9664"])
                ax_metrics.set_xlim(0, 1.05)

            ax_log.set_title("Event Log")
            ax_log.axis("off")
            for i, line in enumerate(sim.world.event_log[-12:]):
                ax_log.text(0, 1 - i * 0.08, line, fontsize=7, family="monospace", transform=ax_log.transAxes)

            return []

        anim = plt.animation.FuncAnimation(fig, update, interval=interval, cache_frame_data=False)
        plt.tight_layout()
        plt.show()


def create_visualizer() -> BaseVisualizer:
    if HAS_PYGAME:
        return PygameVisualizer()
    return MatplotlibVisualizer()
