"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { Room, RoomEvent, Track, VideoTrack, RemoteParticipant, RemoteTrackPublication } from "livekit-client";
import { useChat } from "@/lib/store";

interface LiveKitRoomProps {
  token: string;
  serverUrl: string;
  roomName: string;
  onDisconnect: () => void;
  onSpeakingChange: (isSpeaking: boolean) => void;
  onAvatarVideo?: (videoElement: HTMLVideoElement | null) => void;
  onContextLoaded?: (data: any) => void;
  audioStream?: MediaStream;
}

export default function LiveKitRoom({
  token,
  serverUrl,
  roomName,
  onDisconnect,
  onSpeakingChange,
  onAvatarVideo,
  onContextLoaded,
  audioStream,
}: LiveKitRoomProps) {
  const roomRef = useRef<Room | null>(null);
  const connectedRef = useRef(false);
  const avatarVideoRef = useRef<HTMLVideoElement | null>(null);
  const { addTranscript, addToolCall, setSummary } = useChat();
  
  // Store callbacks in refs
  const onDisconnectRef = useRef(onDisconnect);
  const onSpeakingChangeRef = useRef(onSpeakingChange);
  const onAvatarVideoRef = useRef(onAvatarVideo);
  
  useEffect(() => {
    onDisconnectRef.current = onDisconnect;
    onSpeakingChangeRef.current = onSpeakingChange;
    onAvatarVideoRef.current = onAvatarVideo;
  }, [onDisconnect, onSpeakingChange, onAvatarVideo]);

  useEffect(() => {
    if (connectedRef.current || !token || !serverUrl) return;
    
    let room: Room | null = null;
    let mounted = true;

    const connect = async () => {
      try {
        connectedRef.current = true;
        room = new Room({
          adaptiveStream: true,
          dynacast: true,
        });
        roomRef.current = room;

        // Handle data channel messages
        room.on(RoomEvent.DataReceived, (payload: Uint8Array) => {
          if (!mounted) return;
          try {
            const text = new TextDecoder().decode(payload);
            const data = JSON.parse(text);
            handleAgentEvent(data);
          } catch (err) {
            console.warn("Failed to parse data:", err);
          }
        });

        // Handle track subscriptions (video from avatar, audio from agent)
        room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
          if (!mounted) return;
          console.log(`Track subscribed: ${track.kind} from ${participant.identity}`);
          
          // Video track from avatar
          if (track.kind === Track.Kind.Video) {
            console.log("✅ Avatar video track subscribed");
            const videoEl = document.createElement("video");
            videoEl.autoplay = true;
            videoEl.playsInline = true;
            videoEl.muted = true; // Video is muted, audio comes separately
            videoEl.style.width = "100%";
            videoEl.style.height = "100%";
            videoEl.style.objectFit = "cover";
            
            (track as VideoTrack).attach(videoEl);
            avatarVideoRef.current = videoEl;
            onAvatarVideoRef.current?.(videoEl);
          }
          
          // Audio track from agent (or avatar)
          if (track.kind === Track.Kind.Audio) {
            console.log("✅ Audio track subscribed");
            onSpeakingChangeRef.current(true);
            
            const audioEl = document.createElement("audio");
            audioEl.autoplay = true;
            audioEl.id = `lk-audio-${track.sid}`;
            track.attach(audioEl);
            document.body.appendChild(audioEl);
          }
        });

        room.on(RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
          if (!mounted) return;
          console.log(`Track unsubscribed: ${track.kind} from ${participant.identity}`);
          
          if (track.kind === Track.Kind.Video) {
            if (avatarVideoRef.current) {
              (track as VideoTrack).detach(avatarVideoRef.current);
              avatarVideoRef.current = null;
              onAvatarVideoRef.current?.(null);
            }
          }
          
          if (track.kind === Track.Kind.Audio) {
            onSpeakingChangeRef.current(false);
            const audioEl = document.getElementById(`lk-audio-${track.sid}`);
            audioEl?.remove();
          }
        });

        // Handle participant connections
        room.on(RoomEvent.ParticipantConnected, (participant) => {
          console.log("Participant connected:", participant.identity);
          
          // If this is the avatar participant, explicitly subscribe to its video track
          if (participant.identity === "avatar-agent" || participant.identity.includes("avatar")) {
            console.log("🎭 Avatar participant detected, subscribing to video...");
            
            // Subscribe to video track publications
            participant.videoTrackPublications.forEach((pub) => {
              if (!pub.isSubscribed) {
                console.log(`Subscribing to video track: ${pub.trackSid}`);
                participant.setSubscribed(pub.trackSid, true);
              } else if (pub.track) {
                // Track already subscribed, attach it
                handleExistingTrack(pub.track, participant);
              }
            });
          }
          
          // Subscribe to existing tracks
          participant.trackPublications.forEach((pub) => {
            if (pub.track && pub.isSubscribed) {
              handleExistingTrack(pub.track, participant);
            }
          });
        });

        room.on(RoomEvent.Disconnected, () => {
          if (!mounted) return;
          console.log("Disconnected from room");
          connectedRef.current = false;
          onDisconnectRef.current();
        });

        // Connect
        await room.connect(serverUrl, token);
        console.log("✅ Connected to LiveKit room:", roomName);

        // Check for existing participants and subscribe to avatar video
        room.remoteParticipants.forEach((participant) => {
          console.log("Existing participant:", participant.identity);
          
          // Explicitly subscribe to avatar video tracks
          if (participant.identity === "avatar-agent" || participant.identity.includes("avatar")) {
            console.log("🎭 Found avatar participant, subscribing to video...");
            participant.videoTrackPublications.forEach((pub) => {
              if (!pub.isSubscribed) {
                console.log(`Subscribing to existing video track: ${pub.trackSid}`);
                participant.setSubscribed(pub.trackSid, true);
              } else if (pub.track) {
                // Already subscribed, attach it
                handleExistingTrack(pub.track, participant);
              }
            });
          }
          
          // Handle already subscribed tracks
          participant.trackPublications.forEach((pub) => {
            if (pub.track && pub.isSubscribed) {
              handleExistingTrack(pub.track, participant);
            }
          });
        });

        // Publish microphone
        if (audioStream) {
          try {
            await room.localParticipant.setMicrophoneEnabled(true);
            console.log("✅ Microphone enabled");
          } catch (err) {
            console.warn("Mic enable failed, publishing track:", err);
            const audioTrack = audioStream.getAudioTracks()[0];
            if (audioTrack) {
              await room.localParticipant.publishTrack(audioTrack);
            }
          }
        }

      } catch (error: any) {
        console.error("Failed to connect:", error);
        connectedRef.current = false;
        if (mounted) {
          alert(`Failed to connect: ${error.message}`);
          onDisconnectRef.current();
        }
      }
    };

    const handleExistingTrack = (track: any, participant: RemoteParticipant) => {
      if (track.kind === Track.Kind.Video) {
        console.log("✅ Attaching existing avatar video");
        const videoEl = document.createElement("video");
        videoEl.autoplay = true;
        videoEl.playsInline = true;
        videoEl.muted = true;
        videoEl.style.width = "100%";
        videoEl.style.height = "100%";
        videoEl.style.objectFit = "cover";
        
        (track as VideoTrack).attach(videoEl);
        avatarVideoRef.current = videoEl;
        onAvatarVideoRef.current?.(videoEl);
      }
      
      if (track.kind === Track.Kind.Audio) {
        const audioEl = document.createElement("audio");
        audioEl.autoplay = true;
        audioEl.id = `lk-audio-${track.sid}`;
        track.attach(audioEl);
        document.body.appendChild(audioEl);
      }
    };

    connect();

    return () => {
      mounted = false;
      if (room) {
        room.disconnect();
        roomRef.current = null;
      }
      connectedRef.current = false;
      avatarVideoRef.current = null;
      onAvatarVideoRef.current?.(null);
      document.querySelectorAll("[id^='lk-audio-']").forEach(el => el.remove());
    };
  }, [token, serverUrl, roomName]);

  const handleAgentEvent = useCallback((data: any) => {
    switch (data.type) {
      case "transcript":
        addTranscript({
          role: data.role,
          text: data.text,
          timestamp: data.timestamp || new Date().toISOString(),
        });
        break;
      case "tool_call":
        addToolCall({
          tool: data.tool,
          args: data.args,
          result: data.result,
          timestamp: data.timestamp || new Date().toISOString(),
        });
        break;
      case "summary":
        setSummary(data);
        break;
      case "context_loaded":
        if (onContextLoaded) {
          onContextLoaded(data);
        }
        break;
      case "avatar_ready":
        // Avatar and STT/TTS are now ready
        console.log("✅ Avatar and STT/TTS ready:", data);
        break;
    }
  }, [addTranscript, addToolCall, setSummary, onContextLoaded]);

  return null;
}
