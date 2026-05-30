"""Pygame primary renderer with matplotlib fallback."""

from __future__ import annotations

import sys
from typing import Dict, List, Optional, TYPE_CHECKING

import networkx as nx
import numpy as np

from config import CELL_PX, FPS, GRAPH_HEIGHT, GRID_SIZE, HUD_WIDTH, HISTORY_LEN
from personalities import personality_by_id
from tools import TOOLS

if TYPE_CHECKING:
    from simulation import Simulation

PYGAME_OK = True
try:
    import pygame
except ImportError:
    PYGAME_OK = False


class VisualizerBase:
    def __init__(self, sim: "Simulation") -> None:
        self.sim = sim

    def handle_input(self) -> None:
        pass

    def render(self) -> bool:
        """Return False to quit."""
        return True

    def close(self) -> None:
        pass


if PYGAME_OK:

    class PygameVisualizer(VisualizerBase):
        def __init__(self, sim: "Simulation") -> None:
            super().__init__(sim)
            pygame.init()
            self.map_w = GRID_SIZE * CELL_PX
            self.h = self.map_w + GRAPH_HEIGHT + 40
            self.w = self.map_w + HUD_WIDTH
            self.screen = pygame.display.set_mode((self.w, self.h))
            pygame.display.set_caption("Emergence World Simulation")
            self.clock = pygame.time.Clock()
            self.font = pygame.font.SysFont("dejavusans", 14)
            self.font_sm = pygame.font.SysFont("dejavusans", 11)
            self._accum = 0.0

        def handle_input(self) -> None:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.sim.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        self.sim.running = False
                    elif event.key == pygame.K_SPACE:
                        self.sim.paused = not self.sim.paused
                    elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                        self.sim.speed = min(20.0, self.sim.speed + 0.5)
                    elif event.key == pygame.K_MINUS:
                        self.sim.speed = max(0.25, self.sim.speed - 0.5)
                    elif event.key == pygame.K_TAB:
                        ids = sorted(self.sim.agents.keys())
                        if not self.sim.inspect_id:
                            self.sim.inspect_id = ids[0]
                        else:
                            i = ids.index(self.sim.inspect_id)
                            self.sim.inspect_id = ids[(i + 1) % len(ids)]

        def render(self) -> bool:
            self.handle_input()
            if not self.sim.paused and self.sim.running:
                steps = max(1, int(self.sim.speed))
                self.sim.run_batch(steps)

            self._draw()
            pygame.display.flip()
            self.clock.tick(FPS)
            return self.sim.running

        def _draw(self) -> None:
            s = self.sim
            self.screen.fill((18, 22, 28))

            # Resource heatmap (downsampled)
            res = s.world.resource_map
            step = max(1, GRID_SIZE // (self.map_w // CELL_PX))
            for y in range(0, GRID_SIZE, step):
                for x in range(0, GRID_SIZE, step):
                    v = res[y, x]
                    c = int(30 + v * 80)
                    rect = pygame.Rect(x * CELL_PX, y * CELL_PX, CELL_PX * step, CELL_PX * step)
                    pygame.draw.rect(self.screen, (20, c, 40), rect)

            # Landmarks
            for lm in s.world.landmarks.values():
                px, py = lm.x * CELL_PX, lm.y * CELL_PX
                pygame.draw.rect(self.screen, (220, 180, 60), (px - 2, py - 2, 6, 6))

            # Structures
            for (sx, sy), name in s.world.structures.items():
                pygame.draw.circle(self.screen, (180, 180, 220), (sx * CELL_PX, sy * CELL_PX), 3)

            # Agents
            for agent in s.agents.values():
                if not agent.alive:
                    continue
                col = agent.personality.color
                px, py = agent.x * CELL_PX, agent.y * CELL_PX
                pygame.draw.circle(self.screen, col, (px, py), max(3, CELL_PX // 2))
                if s.inspect_id == agent.id:
                    pygame.draw.circle(self.screen, (255, 255, 255), (px, py), max(5, CELL_PX), 1)

            # Relationship graph panel
            graph_y = self.map_w + 8
            self._draw_graph(graph_y)

            # HUD
            hud_x = self.map_w + 8
            lines = [
                f"Turn {s.turn} / {s.max_turns}  |  Speed {s.speed:.1f}x",
                f"Alive {s.alive_count()}/10  |  {'PAUSED' if s.paused else 'RUNNING'}",
                f"Tools: {TOOLS_COUNT} registered",
                "Controls: Space pause, +/- speed, Tab inspect, Q quit",
                "",
            ]
            if s.inspect_id:
                a = s.agents[s.inspect_id]
                p = a.personality
                lines += [
                    f"— {p.name} ({p.role}) —",
                    f"Energy {a.energy:.0f}  Credits {a.credits}  Inv {a.inventory}",
                    f"Goals: {', '.join(a.goals[:2])}",
                    f"Alliances: {len(a.alliances)}",
                ]
            y = 10
            for line in lines:
                surf = self.font.render(line, True, (220, 225, 235))
                self.screen.blit(surf, (hud_x, y))
                y += 18

            # Energy bars
            y += 6
            for aid in sorted(s.agents.keys()):
                a = s.agents[aid]
                if not a.alive:
                    continue
                bw = 180
                fill = int(bw * (a.energy / 100.0))
                pygame.draw.rect(self.screen, (50, 55, 65), (hud_x, y, bw, 10))
                pygame.draw.rect(
                    self.screen, a.personality.color, (hud_x, y, max(1, fill), 10)
                )
                label = self.font_sm.render(a.personality.name[:8], True, (200, 200, 200))
                self.screen.blit(label, (hud_x + bw + 6, y - 2))
                y += 14

            # Emergence Gazette headlines
            y += 4
            gazette = self.font_sm.render("— The Emergence Gazette —", True, (200, 180, 120))
            self.screen.blit(gazette, (hud_x, y))
            y += 16
            for headline in s.newspaper.latest_headlines(6):
                surf = self.font_sm.render(headline[:42], True, (160, 200, 180))
                self.screen.blit(surf, (hud_x, y))
                y += 14

        def _draw_graph(self, y0: int) -> None:
            g = self.sim.rel.to_undirected_view()
            panel = pygame.Rect(4, y0, self.map_w - 8, GRAPH_HEIGHT)
            pygame.draw.rect(self.screen, (28, 32, 40), panel)
            if g.number_of_nodes() == 0:
                return
            pos = nx.spring_layout(g, seed=42, k=0.9)
            xs = [pos[n][0] for n in g.nodes()]
            ys = [pos[n][1] for n in g.nodes()]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)

            def tx(nx_: float) -> int:
                return int(panel.x + 20 + (nx_ - min_x) / (max_x - min_x + 1e-6) * (panel.w - 40))

            def ty(ny_: float) -> int:
                return int(panel.y + 20 + (ny_ - min_y) / (max_y - min_y + 1e-6) * (panel.h - 40))

            for u, v, d in g.edges(data=True):
                w = d.get("weight", 0)
                col = (80, 200, 120) if w >= 0 else (200, 80, 80)
                pygame.draw.line(
                    self.screen, col, (tx(pos[u][0]), ty(pos[u][1])), (tx(pos[v][0]), ty(pos[v][1])), 1
                )
            for n in g.nodes():
                try:
                    col = personality_by_id(n).color
                except KeyError:
                    col = (200, 200, 200)
                pygame.draw.circle(self.screen, col, (tx(pos[n][0]), ty(pos[n][1])), 5)

        def close(self) -> None:
            pygame.quit()


TOOLS_COUNT = TOOLS.count()


def create_visualizer(sim: "Simulation") -> VisualizerBase:
    if PYGAME_OK:
        return PygameVisualizer(sim)
    return MatplotlibVisualizer(sim)


class MatplotlibVisualizer(VisualizerBase):
    """Fallback animated dashboard."""

    def __init__(self, sim: "Simulation") -> None:
        super().__init__(sim)
        import matplotlib.pyplot as plt

        self.plt = plt
        self.plt.ion()
        self.fig, self.axes = self.plt.subplots(2, 2, figsize=(12, 9))
        self.fig.suptitle("Emergence World (matplotlib fallback)")

    def _update(self, frame: int) -> None:
        s = self.sim
        ax0, ax1, ax2, ax3 = self.axes.flat
        for ax in self.axes.flat:
            ax.clear()

        ax0.imshow(s.world.resource_map, cmap="viridis", origin="upper")
        for lm in s.world.landmarks.values():
            ax0.plot(lm.x, lm.y, "y*", markersize=4)
        for a in s.agents.values():
            if a.alive:
                ax0.plot(a.x, a.y, "o", color=[c / 255 for c in a.personality.color], markersize=6)
        ax0.set_title(f"World T{s.turn}")

        g = s.rel.to_undirected_view()
        if g.number_of_edges() > 0:
            pos = nx.spring_layout(g, seed=42)
            colors = ["green" if d["weight"] >= 0 else "red" for _, _, d in g.edges(data=True)]
            nx.draw(g, pos, ax=ax1, with_labels=True, edge_color=colors, node_size=400, font_size=7)
        ax1.set_title("Relationships")

        if s.metrics_history:
            keys = list(s.metrics_history[-1].keys())
            for k in keys[:5]:
                ax2.plot([m[k] for m in s.metrics_history[-HISTORY_LEN:]], label=k)
            ax2.legend(fontsize=6)
        ax2.set_title("Metrics")

        names, energy = [], []
        for a in s.agents.values():
            if a.alive:
                names.append(a.personality.name)
                energy.append(a.energy)
        ax3.barh(names, energy, color="teal")
        ax3.set_title("Energy")
        self.fig.canvas.draw_idle()
        self.plt.pause(0.02)

    def render(self) -> bool:
        if not self.sim.paused and self.sim.running:
            self.sim.run_batch(max(1, int(self.sim.speed)))
        self._update(0)
        if self.sim.turn >= self.sim.max_turns:
            self.sim.running = False
        return self.sim.running

    def close(self) -> None:
        self.plt.close("all")
